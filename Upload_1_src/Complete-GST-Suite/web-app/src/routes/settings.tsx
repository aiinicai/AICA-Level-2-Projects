import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ShieldCheck, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader, Panel, StatusBadge, Term } from "@/components/gst/common";
import { DataTable } from "@/components/gst/DataTable";
import { FirmForm } from "@/components/gst/FirmForm";
import { validateGstin } from "@/lib/gst/gstin";
import { DEFAULT_GSP_ENDPOINTS } from "@/lib/gst/gsp";
import { downloadTemplate } from "@/lib/exports";
import { DEMO_FIRM, applyRetention, useCurrentUser, deleteClientData, log, newId, removeUser, resetAll, saveUser, setState, useApp, useClients, type Firm, type User } from "@/lib/store";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Complete GST Suite" },
      { name: "description", content: "Firm profile, staff and roles, GSP credentials, tolerance, reminders, templates and data retention." },
      { property: "og:title", content: "Settings — Complete GST Suite" },
      { property: "og:description", content: "Firm, staff, GSP, preferences and data settings." },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const firm = useApp((s) => s.firm);
  const prefs = useApp((s) => s.prefs);
  const dark = useApp((s) => s.dark);
  const partner = useCurrentUser().role === "Partner";
  const [f, setF] = useState<Firm>(firm ?? { ...DEMO_FIRM, name: "", frn: "", partner: "", city: "" });
  useEffect(() => { if (firm) setF(firm); }, [firm]);
  const setPref = (p: Partial<typeof prefs>) => setState((s) => ({ prefs: { ...s.prefs, ...p } }));

  return (
    <div className="max-w-5xl">
      <PageHeader title="Settings" subtitle={partner ? "You are a Partner — you can change everything here." : "You are signed in as Staff — firm, staff, GSP and data settings need a Partner."} />
      <Tabs defaultValue="firm">
        <div className="overflow-x-auto"><TabsList>
          <TabsTrigger value="firm">Firm profile</TabsTrigger>
          <TabsTrigger value="staff">Staff &amp; roles</TabsTrigger>
          <TabsTrigger value="gsp">GSP</TabsTrigger>
          <TabsTrigger value="prefs">Preferences</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="data">Data</TabsTrigger>
        </TabsList></div>
        <TabsContent value="firm" className="mt-6 space-y-6">
          <Panel title="Firm profile">
            <fieldset disabled={!partner}><FirmForm value={f} onChange={setF} /></fieldset>
            <div className="mt-4 flex justify-end">
              <Button disabled={!partner} onClick={() => { if (f.gstin && !validateGstin(f.gstin).valid) return void toast.error("Please fix the GSTIN first"); setState({ firm: f }); log("Updated firm profile"); toast.success("Firm profile saved"); }}>Save</Button>
            </div>
          </Panel>
          <Panel title="Appearance">
            <div className="flex items-center justify-between"><Label htmlFor="dark">Dark mode</Label><Switch id="dark" checked={dark} onCheckedChange={(v) => setState({ dark: v })} /></div>
          </Panel>
          <Panel title="Security">
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex gap-2"><ShieldCheck className="h-4 w-4 shrink-0 text-success" /> No GST portal password is ever asked for or stored. Portal access is only through a GSP using the client's OTP, or files you download yourself.</li>
              <li className="flex gap-2"><ShieldCheck className="h-4 w-4 shrink-0 text-success" /> Only an opaque GSP session reference and its expiry are kept; tokens refresh automatically before expiry.</li>
              <li className="flex gap-2"><ShieldCheck className="h-4 w-4 shrink-0 text-success" /> Partners see all clients; Staff see only clients assigned to them — on every screen and export.</li>
            </ul>
          </Panel>
        </TabsContent>
        <TabsContent value="staff" className="mt-6"><StaffTab partner={partner} /></TabsContent>
        <TabsContent value="gsp" className="mt-6"><GspTab partner={partner} /></TabsContent>
        <TabsContent value="prefs" className="mt-6">
          <Panel title="Reconciliation & reminders">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5"><Label htmlFor="tol"><Term k="Tolerance">Rounding tolerance (₹)</Term></Label><Input id="tol" type="number" min={0} value={prefs.tolerance} onChange={(e) => setPref({ tolerance: Math.max(0, Number(e.target.value) || 0) })} /></div>
              <div className="space-y-1.5"><Label htmlFor="soon">“Due soon” window for notices (days)</Label><Input id="soon" type="number" min={1} value={prefs.reminderDays} onChange={(e) => setPref({ reminderDays: Math.max(1, Number(e.target.value) || 7) })} /></div>
              <div className="space-y-1.5"><Label htmlFor="rem">E-mail reminder to assigned staff — days before due date</Label><Input id="rem" type="number" min={0} value={prefs.emailReminderDays} onChange={(e) => setPref({ emailReminderDays: Math.max(0, Number(e.target.value) || 0) })} /></div>
              <div className="space-y-1.5">
                <Label htmlFor="dfy">Default financial year</Label>
                <select id="dfy" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={prefs.defaultFy} onChange={(e) => setPref({ defaultFy: e.target.value })}>
                  {["2023-24", "2024-25", "2025-26", "2026-27"].map((y) => <option key={y}>{y}</option>)}
                </select>
              </div>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">A new tolerance applies to the next run. Reminders open a ready-to-send e-mail to each assigned staff member (Notices › Remind staff).</p>
          </Panel>
        </TabsContent>
        <TabsContent value="templates" className="mt-6">
          <Panel title="Download templates">
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void downloadTemplate("client-master")}>Client master</Button>
              <Button variant="outline" onClick={() => void downloadTemplate("gstr3b-summary")}>GSTR-3B 12-month summary</Button>
              <Button variant="outline" onClick={() => void downloadTemplate("notices")}>Manual notices</Button>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">The client master has no password column — portal access is only through a GSP with the client's OTP.</p>
          </Panel>
        </TabsContent>
        <TabsContent value="data" className="mt-6"><DataTab partner={partner} /></TabsContent>
      </Tabs>
    </div>
  );
}

function StaffTab({ partner }: { partner: boolean }) {
  const users = useApp((s) => s.users);
  const clients = useApp((s) => s.clients);
  const [u, setU] = useState<User>({ id: "", name: "", email: "", role: "Staff" });
  return (
    <div className="space-y-6">
      <Panel title="Staff and roles">
        <p className="mb-3 text-sm text-muted-foreground">Partner = all clients. Staff = only the clients where they are the assigned staff (set in the client master). Use the user menu (top right) to work as any of them.</p>
        <DataTable rows={users} rowKey={(x) => x.id} exportName="staff" empty={{ message: "No staff." }}
          columns={[
            { key: "name", title: "Name", header: "Name", value: (x) => x.name },
            { key: "email", title: "E-mail", header: "E-mail", value: (x) => x.email },
            { key: "role", title: "Role", header: "Role", value: (x) => x.role, filter: true, cell: (x) => <StatusBadge status={x.role === "Partner" ? "Open" : "neutral"} label={x.role} /> },
            { key: "clients", title: "Clients", header: "Clients", value: (x) => (x.role === "Partner" ? clients.length : clients.filter((c) => c.staff === x.name).length), align: "right" },
            { key: "act", title: "", header: "", value: () => "", noExport: true, cell: (x) => partner ? (
              <div className="flex gap-1">
                <Button size="sm" variant="ghost" onClick={() => setU(x)}>Edit</Button>
                <Button size="icon" variant="ghost" className="h-8 w-8" aria-label={`Remove ${x.name}`} onClick={() => { try { removeUser(x.id); toast.success("Removed"); } catch (e) { toast.error(e instanceof Error ? e.message : String(e)); } }}><Trash2 className="h-4 w-4" /></Button>
              </div>) : null },
          ]} />
      </Panel>
      {partner && (
        <Panel title={u.id ? "Edit staff member" : "Add staff member"}>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5"><Label htmlFor="s-name">Name</Label><Input id="s-name" value={u.name} onChange={(e) => setU({ ...u, name: e.target.value })} /></div>
            <div className="space-y-1.5"><Label htmlFor="s-email">E-mail</Label><Input id="s-email" type="email" value={u.email} onChange={(e) => setU({ ...u, email: e.target.value })} /></div>
            <div className="space-y-1.5"><Label htmlFor="s-role">Role</Label><select id="s-role" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={u.role} onChange={(e) => setU({ ...u, role: e.target.value as User["role"] })}><option>Staff</option><option>Partner</option></select></div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            {u.id && <Button variant="ghost" onClick={() => setU({ id: "", name: "", email: "", role: "Staff" })}>Cancel</Button>}
            <Button onClick={() => { if (!u.name.trim() || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(u.email)) return void toast.error("Enter a name and a valid e-mail"); saveUser({ ...u, id: u.id || "u-" + newId() }); setU({ id: "", name: "", email: "", role: "Staff" }); toast.success("Staff saved"); }}>Save staff</Button>
          </div>
        </Panel>
      )}
    </div>
  );
}

function GspTab({ partner }: { partner: boolean }) {
  const gsp = useApp((s) => s.gsp);
  const [g, setG] = useState(gsp);
  const [secret, setSecret] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => setG(gsp), [gsp]);
  return (
    <Panel title={<Term k="GSP">GSP (GST Suvidha Provider) settings</Term>} actions={<StatusBadge status={g.baseUrl && g.secretConfigured ? "Matched" : "neutral"} label={g.baseUrl && g.secretConfigured ? "Live GSP configured" : "Demo GSP (OTP 123456)"} />}>
      <fieldset disabled={!partner} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-1.5"><Label htmlFor="g-url">GSP base URL</Label><Input id="g-url" placeholder="https://api.your-gsp.com" value={g.baseUrl} onChange={(e) => setG({ ...g, baseUrl: e.target.value })} /></div>
          <div className="space-y-1.5"><Label htmlFor="g-id">Client id</Label><Input id="g-id" type="password" autoComplete="off" value={g.clientId} onChange={(e) => setG({ ...g, clientId: e.target.value })} /></div>
          <div className="space-y-1.5"><Label htmlFor="g-sec">Client secret</Label><Input id="g-sec" type="password" autoComplete="new-password" placeholder={g.secretConfigured ? "•••••••• saved — type to replace" : "Enter GSP client secret"} value={secret} onChange={(e) => setSecret(e.target.value)} /></div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="g-ep">Endpoint paths (one config object — change for any GSP)</Label>
          <Textarea id="g-ep" rows={12} className="font-mono text-xs" value={g.endpoints} onChange={(e) => setG({ ...g, endpoints: e.target.value })} />
          <p className="text-xs text-muted-foreground">authenticate (OTPREQUEST / AUTHTOKEN / REFRESHTOKEN), gstr1 (B2B, B2CS, CDNR), gstr2b (GET2B), gstr3b (RETSUM), notices.</p>
        </div>
        {err && <p className="text-sm text-destructive">{err}</p>}
        <div className="flex justify-between gap-2">
          <Button variant="ghost" onClick={() => setG({ ...g, endpoints: JSON.stringify(DEFAULT_GSP_ENDPOINTS, null, 2) })}>Reset endpoints</Button>
          <Button onClick={() => {
            try { JSON.parse(g.endpoints); } catch { return setErr("The endpoint config is not valid JSON."); }
            setErr("");
            setState({ gsp: { ...g, secretConfigured: g.secretConfigured || !!secret } });
            setSecret("");
            log("GSP settings changed");
            toast.success("GSP settings saved");
          }}>Save GSP settings</Button>
        </div>
      </fieldset>
      <p className="mt-4 rounded-md bg-muted p-3 text-xs text-muted-foreground">These are the firm's GSP API credentials — never a client's GST portal password. The client secret is never kept in the browser: store it as a server secret (GSP_CLIENT_SECRET) in the hosting project's Secrets, where server-side GSP calls read it. Until a live GSP is wired up, the built-in demo GSP is used (OTP 123456).</p>
    </Panel>
  );
}

function DataTab({ partner }: { partner: boolean }) {
  const prefs = useApp((s) => s.prefs);
  const clients = useClients();
  const [years, setYears] = useState(prefs.retentionYears);
  const [cid, setCid] = useState("");
  const [remove, setRemove] = useState(false);
  return (
    <div className="space-y-6">
      <Panel title="Data retention">
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5"><Label htmlFor="ret">Keep run history and activity log for (years)</Label><Input id="ret" type="number" min={1} max={20} className="w-32" value={years} onChange={(e) => setYears(Math.max(1, Number(e.target.value) || 8))} /></div>
          <Button variant="outline" disabled={!partner} onClick={() => { applyRetention(years); toast.success("Retention applied"); }}>Save &amp; apply</Button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">GST records must generally be kept for 72 months from the due date of the annual return.</p>
      </Panel>
      <Panel title="Delete client data">
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5"><Label htmlFor="del-c">Client</Label><select id="del-c" className="h-9 w-72 rounded-md border bg-background px-2 text-sm" value={cid} onChange={(e) => setCid(e.target.value)}><option value="">Choose client…</option>{clients.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.gstin})</option>)}</select></div>
          <label className="flex items-center gap-2 text-sm"><Switch checked={remove} onCheckedChange={setRemove} /> Also remove the client from the client master</label>
          <Button variant="destructive" disabled={!partner || !cid} onClick={() => { if (confirm("This permanently deletes uploaded files, fetched returns, runs, notices and draft edits for this client. Continue?")) { deleteClientData(cid, remove); setCid(""); toast.success("Client data deleted"); } }}>Delete client data</Button>
        </div>
      </Panel>
      <Panel title="Start again">
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">Clear the demo firm, clients, uploads, runs, notices and activity.</p>
          <Button variant="outline" disabled={!partner} onClick={() => { if (confirm("Clear everything?")) { resetAll(); toast.success("Everything cleared"); } }}>Reset all data</Button>
        </div>
      </Panel>
    </div>
  );
}
