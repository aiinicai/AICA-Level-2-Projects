import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Building2, Database, FlaskConical, Plus, Upload } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { exportBackup, logAudit, restoreBackup, run, uid } from "@/lib/db";
import { GSTIN_RE } from "@/lib/import";
import { REG_TYPES, STATES } from "@/lib/types";
import { useClients, useRefresh } from "@/lib/useData";
import { DEMO_LABEL, isDemoClient, loadDemoData } from "@/lib/demoData";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "GST Annual Return Reconciliation — Client Workspace" },
      { name: "description", content: "Offline GST annual return reconciliation for Chartered Accountants: compare Tally books with GSTR-1, 3B, 2B, 9 and 9C." },
      { property: "og:title", content: "GST Annual Return Reconciliation" },
      { property: "og:description", content: "Compare Tally books with GSTR-1, GSTR-3B, GSTR-2B, GSTR-9 and GSTR-9C — entirely offline." },
    ],
  }),
  component: ClientsPage,
});

const FYS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"];

function ClientsPage() {
  const clients = useClients();
  const refresh = useRefresh();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", gstin: "", fy: "2024-25", state: "Maharashtra", reg_type: "Regular" });
  const [errors, setErrors] = useState<string[]>([]);
  const [loadingDemo, setLoadingDemo] = useState(false);

  async function create() {
    const errs: string[] = [];
    if (!form.name.trim()) errs.push("Client name is required.");
    if (!GSTIN_RE.test(form.gstin.trim().toUpperCase())) errs.push("Please enter a valid 15-character GSTIN (e.g. 27AAAAA0000A1Z5).");
    setErrors(errs);
    if (errs.length) return;
    const id = uid();
    await run("INSERT INTO clients (id, name, gstin, fy, state, reg_type, created_at) VALUES (?,?,?,?,?,?,?)", [
      id, form.name.trim(), form.gstin.trim().toUpperCase(), form.fy, form.state, form.reg_type, new Date().toISOString(),
    ]);
    await logAudit(id, "Client created", `${form.name} · ${form.gstin} · FY ${form.fy}`);
    refresh(["clients"]);
    toast.success("Client created.");
    navigate({ to: "/clients/$id", params: { id } });
  }

  async function backup() {
    const blob = await exportBackup();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gst-reconciliation-backup-${new Date().toISOString().slice(0, 10)}.sqlite`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Backup file saved.");
  }

  async function restore(file: File) {
    await restoreBackup(new Uint8Array(await file.arrayBuffer()));
    refresh(["clients", "txns", "imports", "recon", "audit", "settings"]);
    toast.success("Backup restored.");
  }

  async function demo() {
    setLoadingDemo(true);
    try {
      const id = await loadDemoData();
      refresh(["clients", "txns", "imports", "recon", "audit"]);
      toast.success("Demo client loaded with sample reconciliation data.");
      navigate({ to: "/clients/$id", params: { id } });
    } finally {
      setLoadingDemo(false);
    }
  }

  return (
    <AppShell>
      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Clients</CardTitle>
            <span className="text-xs text-muted-foreground">{clients.data?.length ?? 0} saved locally</span>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Client</TableHead>
                  <TableHead>GSTIN</TableHead>
                  <TableHead>Financial year</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Registration</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(clients.data ?? []).map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">
                      {c.name}
                      {isDemoClient(c.name) && (
                        <span className="ml-2 rounded border border-amber-500/50 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                          {DEMO_LABEL}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{c.gstin}</TableCell>
                    <TableCell>{c.fy}</TableCell>
                    <TableCell>{c.state}</TableCell>
                    <TableCell>{c.reg_type}</TableCell>
                    <TableCell>
                      <Link to="/clients/$id" params={{ id: c.id }}>
                        <Button size="sm" variant="outline">Open</Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
                {(clients.data ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="py-12 text-center text-sm text-muted-foreground">
                      <Building2 className="mx-auto mb-2 h-6 w-6" />
                      No clients yet. Create your first client to begin a reconciliation.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="border-amber-500/50 bg-amber-500/5">
            <CardHeader><CardTitle className="text-base">Try it with sample data</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-muted-foreground">
                Creates a fictitious client for FY 2025-26 with Tally, GSTR-1, 3B, 2B, 9 and previous-year data —
                including deliberate missing invoices, value mismatches and invoice-number mismatches.
              </p>
              <p className="rounded border border-amber-500/50 bg-amber-500/10 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                {DEMO_LABEL}
              </p>
              <Button variant="outline" className="w-full" onClick={demo} disabled={loadingDemo}>
                <FlaskConical className="mr-2 h-4 w-4" /> {loadingDemo ? "Loading demo data…" : "Load Demo Data"}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">New client</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1"><Label>Client name</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="ABC Enterprises Pvt Ltd" /></div>
              <div className="space-y-1"><Label>GSTIN</Label>
                <Input value={form.gstin} onChange={(e) => setForm({ ...form, gstin: e.target.value.toUpperCase() })} placeholder="27AAAAA0000A1Z5" className="font-mono" /></div>
              <div className="space-y-1"><Label>Financial year</Label>
                <Select value={form.fy} onValueChange={(v) => setForm({ ...form, fy: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{FYS.map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}</SelectContent>
                </Select></div>
              <div className="space-y-1"><Label>State</Label>
                <Select value={form.state} onValueChange={(v) => setForm({ ...form, state: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{STATES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select></div>
              <div className="space-y-1"><Label>GST registration type</Label>
                <Select value={form.reg_type} onValueChange={(v) => setForm({ ...form, reg_type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{REG_TYPES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select></div>
              {errors.length > 0 && (
                <ul className="rounded border border-destructive/40 bg-destructive/10 p-2 text-xs text-destructive">
                  {errors.map((e) => <li key={e}>{e}</li>)}
                </ul>
              )}
              <Button className="w-full" onClick={create}><Plus className="mr-2 h-4 w-4" /> Create client</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Backup and restore</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-muted-foreground">
                All data is stored in a local SQLite database on this computer. Nothing is uploaded anywhere.
              </p>
              <Button variant="outline" className="w-full" onClick={backup}>
                <Database className="mr-2 h-4 w-4" /> Save backup file
              </Button>
              <div className="space-y-1">
                <Label className="text-xs">Restore from backup</Label>
                <input
                  type="file"
                  accept=".sqlite,.db"
                  className="block w-full cursor-pointer rounded border border-input bg-card p-2 text-sm"
                  onChange={(e) => e.target.files?.[0] && restore(e.target.files[0])}
                />
              </div>
              <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <Upload className="h-3 w-3" /> Restoring replaces the current database.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
