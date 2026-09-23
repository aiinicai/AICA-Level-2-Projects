import { createFileRoute, Link } from "@tanstack/react-router";
import { CreditCard, Lock, Palette, Plug, SlidersHorizontal, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/common/states";
import { InstallAppButton } from "@/components/pwa/InstallAppButton";
import { useWorkspace } from "@/lib/store";
import type { WorkspaceSettings } from "@/lib/types";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — The DASH" },
      { name: "description", content: "Workspace name, currency, number format, timezone, appearance, notifications and security." },
      { property: "og:title", content: "Settings — The DASH" },
      { property: "og:description", content: "Localisation, appearance, notifications, team and security settings." },
    ],
  }),
  component: SettingsPage,
});

const TIMEZONES = ["Asia/Kolkata", "Asia/Dubai", "Europe/London", "America/New_York", "UTC"];

function SettingsPage() {
  const { settings, updateSettings, resetWorkspace } = useWorkspace();

  const set = (patch: Partial<WorkspaceSettings>) => {
    updateSettings(patch);
    toast.success("Settings saved");
  };

  return (
    <div className="pb-10">
      <PageHeader title="Settings" description="Workspace preferences, localisation and access." />

      <div className="px-4 py-6 sm:px-6 lg:px-8">
        <Tabs defaultValue="general">
          <TabsList className="flex w-full flex-wrap justify-start">
            <TabsTrigger value="general"><SlidersHorizontal className="size-4" aria-hidden /> General</TabsTrigger>
            <TabsTrigger value="appearance"><Palette className="size-4" aria-hidden /> Appearance</TabsTrigger>
            <TabsTrigger value="integrations"><Plug className="size-4" aria-hidden /> Integrations</TabsTrigger>
            <TabsTrigger value="security"><Lock className="size-4" aria-hidden /> Security</TabsTrigger>
            <TabsTrigger value="billing"><CreditCard className="size-4" aria-hidden /> Billing</TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="mt-4 space-y-4">
            <section className="panel max-w-2xl space-y-4 p-5">
              <h2 className="text-sm font-semibold">Workspace</h2>
              <div className="space-y-1.5">
                <Label htmlFor="ws-name">Workspace name</Label>
                <Input
                  id="ws-name"
                  defaultValue={settings.workspaceName}
                  onBlur={(e) => set({ workspaceName: e.target.value || settings.workspaceName })}
                />
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Currency</Label>
                  <Select
                    value={settings.currency}
                    onValueChange={(v) => set({ currency: v as WorkspaceSettings["currency"] })}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {["INR", "USD", "EUR", "GBP", "AED"].map((c) => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Number format</Label>
                  <Select
                    value={settings.numberSystem}
                    onValueChange={(v) => set({ numberSystem: v as WorkspaceSettings["numberSystem"] })}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="indian">Indian (1,25,000)</SelectItem>
                      <SelectItem value="international">International (125,000)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Date format</Label>
                  <Select
                    value={settings.dateFormat}
                    onValueChange={(v) => set({ dateFormat: v as WorkspaceSettings["dateFormat"] })}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"].map((f) => (
                        <SelectItem key={f} value={f}>{f}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Timezone</Label>
                  <Select value={settings.timezone} onValueChange={(v) => set({ timezone: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {TIMEZONES.map((t) => (
                        <SelectItem key={t} value={t}>{t}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <Label className="text-sm font-normal">Compact numbers (Lakh / Crore)</Label>
                  <p className="text-xs text-muted-foreground">Show ₹24.8L instead of ₹24,80,000 on cards.</p>
                </div>
                <Switch checked={settings.compactNumbers} onCheckedChange={(v) => set({ compactNumbers: v })} />
              </div>
            </section>
          </TabsContent>

          <TabsContent value="appearance" className="mt-4">
            <section className="panel max-w-2xl space-y-4 p-5">
              <h2 className="text-sm font-semibold">Appearance</h2>
              <div className="space-y-1.5">
                <Label>Theme</Label>
                <Select value={settings.theme} onValueChange={(v) => set({ theme: v as WorkspaceSettings["theme"] })}>
                  <SelectTrigger className="max-w-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="dark">Dark</SelectItem>
                    <SelectItem value="system">Match system</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Install the app</Label>
                <p className="text-xs text-muted-foreground">
                  Add The DASH to your home screen or desktop for a full-screen, offline-tolerant experience.
                </p>
                <InstallAppButton variant="menu" />
              </div>
            </section>
          </TabsContent>

          <TabsContent value="integrations" className="mt-4">
            <section className="panel max-w-2xl space-y-3 p-5">
              <h2 className="text-sm font-semibold">Integrations</h2>
              <p className="text-sm text-muted-foreground">
                Connect accounting, payments, CRM and e-commerce systems, or monitor the sync health of what's already
                connected.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button asChild>
                  <Link to="/integrations">Browse marketplace</Link>
                </Button>
                <Button variant="outline" asChild>
                  <Link to="/data-sources">Sync status</Link>
                </Button>
              </div>
            </section>
          </TabsContent>

          <TabsContent value="security" className="mt-4">
            <section className="panel max-w-2xl space-y-3 p-5">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <Users className="size-4 text-primary" aria-hidden /> Access and security
              </h2>
              <p className="text-sm text-muted-foreground">
                Provider credentials are stored as server-side secrets and are never exposed to the browser. Member
                roles control what each person can see and change.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" asChild>
                  <Link to="/team">Manage team roles</Link>
                </Button>
                <Button
                  variant="ghost"
                  className="text-destructive"
                  onClick={() => {
                    resetWorkspace();
                    toast.success("Workspace reset to demo defaults");
                  }}
                >
                  Reset demo workspace
                </Button>
              </div>
            </section>
          </TabsContent>

          <TabsContent value="billing" className="mt-4">
            <section className="panel max-w-2xl space-y-2 p-5">
              <h2 className="text-sm font-semibold">Billing</h2>
              <p className="text-sm text-muted-foreground">
                Billing isn't enabled on this workspace yet. When it is, your plan, invoices and payment method will
                appear here.
              </p>
            </section>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
