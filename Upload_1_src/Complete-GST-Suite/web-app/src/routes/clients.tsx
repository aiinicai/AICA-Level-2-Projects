import { useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Download, Pencil, Plus, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { PageHeader, Panel, StatusBadge, Term } from "@/components/gst/common";
import { DataTable, type Column } from "@/components/gst/DataTable";
import { DATA_SOURCES, type Client, type DataSource } from "@/lib/gst/demo";
import { fmtDate, fmtDateTime } from "@/lib/gst/format";
import { validateGstin } from "@/lib/gst/gstin";
import { parseClientRows, validateClient, type ClientInput } from "@/lib/gst/parsers";
import { sessionStatus } from "@/lib/gst/gsp";
import { useCurrentUser, deleteClientData, latestRun, loadDemoFirm, newId, runAll, saveClient, updateClients, useApp, useClients } from "@/lib/store";

export const Route = createFileRoute("/clients")({
  head: () => ({
    meta: [
      { title: "Clients — Complete GST Suite" },
      { name: "description", content: "Client master: GSTIN, portal username, data source, API access, assigned staff and latest reconciliation." },
      { property: "og:title", content: "Clients — Complete GST Suite" },
      { property: "og:description", content: "Client master with import from Excel and bulk actions." },
    ],
  }),
  component: ClientsPage,
});

const blank = (): Client => ({
  id: "c-" + newId(), name: "", tradeName: "", gstin: "", portalUsername: "", mobile4: "", email: "", frequency: "Monthly", fy: "2025-26", tallyCompany: "",
  apiEnabled: false, apiValidTill: "", staff: "", fetchReturns: true, fetchNotices: true, active: true, dataSource: "Auto", remarks: "",
  state: "", city: "", business: "", contact: "", filing: "Monthly", note: "", demo: false,
});

interface Row { c: Client; session: string; result: string; last: string }

function ClientsPage() {
  const navigate = useNavigate();
  const clients = useClients();
  const all = useApp((s) => s.clients);
  const runs = useApp((s) => s.runs);
  const sessions = useApp((s) => s.sessions);
  const users = useApp((s) => s.users);
  const [editing, setEditing] = useState<{ c: Client; isNew: boolean } | null>(null);
  const [importing, setImporting] = useState<ReturnType<typeof parseClientRows> | null>(null);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const file = useRef<HTMLInputElement>(null);
  const partner = useCurrentUser().role === "Partner";

  const rows: Row[] = clients.map((c) => {
    const r = latestRun(runs, c.id);
    return {
      c, session: sessionStatus(sessions[c.id]),
      result: !r ? "Not run" : r.status === "Failed" ? "Failed" : r.summary?.partialMonths.length ? "Partial data" : r.summary?.differences ? "Difference" : "Matched",
      last: r ? fmtDateTime(r.at) : "—",
    };
  });

  const cols: Column<Row>[] = [
    { key: "name", title: "Client name", header: "Client", value: (r) => r.c.name, cell: (r) => <div><span className="font-medium text-primary">{r.c.name}</span><div className="text-xs text-muted-foreground">{r.c.tradeName !== r.c.name ? r.c.tradeName : r.c.business}</div></div> },
    { key: "gstin", title: "GSTIN", header: <Term k="GSTIN" />, value: (r) => r.c.gstin, cell: (r) => <span className="font-mono text-xs">{r.c.gstin} {!validateGstin(r.c.gstin).valid && <StatusBadge status="Failed" label="Check" />}</span> },
    { key: "user", title: "Portal username", header: "Portal username", value: (r) => r.c.portalUsername },
    { key: "staff", title: "Staff", header: "Assigned staff", value: (r) => r.c.staff || "(unassigned)", filter: true },
    { key: "ds", title: "Data source", header: <Term k="Data source">Data source</Term>, value: (r) => r.c.dataSource, filter: true },
    { key: "api", title: "API status", header: "API access", value: (r) => (r.c.apiEnabled ? "Enabled" : "Not enabled"), filter: true, cell: (r) => <span>{r.c.apiEnabled ? <StatusBadge status="Matched" label="Enabled" /> : <StatusBadge status="neutral" label="Not enabled" />}{r.c.apiValidTill && <div className="text-[11px] text-muted-foreground">till {fmtDate(r.c.apiValidTill)}</div>}</span> },
    { key: "session", title: "Session status", header: <Term k="GSP">GSP session</Term>, value: (r) => r.session, filter: true, cell: (r) => <StatusBadge status={r.session === "Connected" ? "Matched" : r.session === "Expired" ? "Overdue" : "neutral"} label={r.session} /> },
    { key: "freq", title: "Frequency", header: "Frequency", value: (r) => r.c.frequency },
    { key: "active", title: "Active", header: "Active", value: (r) => (r.c.active ? "Active" : "Inactive"), filter: true },
    { key: "result", title: "Last result", header: "Last result", value: (r) => r.result, cell: (r) => <StatusBadge status={r.result} /> },
    { key: "last", title: "Last run", header: "Last run", value: (r) => r.last, cell: (r) => <span className="whitespace-nowrap text-xs text-muted-foreground">{r.last}</span> },
    { key: "edit", title: "", header: "", value: () => "", noExport: true, cell: (r) => <Button size="icon" variant="ghost" aria-label={`Edit ${r.c.name}`} onClick={(e) => { e.stopPropagation(); setEditing({ c: r.c, isNew: false }); }}><Pencil className="h-4 w-4" /></Button> },
  ];

  const ids = [...sel];
  const bulk = (patch: Partial<Client>, what: string) => { updateClients(ids, patch, what); toast.success(`${what} — ${ids.length} client(s)`); };

  async function onImport(f: File) {
    try {
      const { readSheetRows } = await import("@/lib/gst/excel");
      const parsed = parseClientRows(await readSheetRows(f), all.map((c) => c.gstin));
      if (!parsed.length) return void toast.error("No client rows were found in this file.");
      setImporting(parsed);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not read the file");
    }
  }
  async function template() {
    const x = await import("@/lib/gst/excel");
    x.downloadBlob(x.TEMPLATE_NAMES["client-master"], await x.buildTemplate("client-master"));
  }

  return (
    <div>
      <PageHeader
        title="Clients"
        subtitle="Client master. Open a client to see its reconciliation, annual return drafts, files and notices."
        actions={
          <>
            <Button variant="outline" onClick={() => void template()}><Download className="mr-2 h-4 w-4" /> Template</Button>
            <Button variant="outline" onClick={() => file.current?.click()}><Upload className="mr-2 h-4 w-4" /> Import from Excel</Button>
            <input ref={file} type="file" accept=".xlsx,.xlsm,.csv" className="hidden" aria-label="Client master file" onChange={(e) => { const f = e.target.files?.[0]; if (f) void onImport(f); e.target.value = ""; }} />
            <Button onClick={() => setEditing({ c: blank(), isNew: true })}><Plus className="mr-2 h-4 w-4" /> Add client</Button>
          </>
        }
      />
      <Panel>
        <DataTable
          rows={rows}
          columns={cols}
          rowKey={(r) => r.c.id}
          exportName="client_master"
          onRowClick={(r) => navigate({ to: "/workspace/$clientId", params: { clientId: r.c.id }, search: { tab: "overview" } })}
          selection={{ selected: sel, onChange: setSel }}
          rowClassName={(r) => (!r.c.active ? "opacity-60" : "")}
          empty={{ message: "No clients yet. Add one, import your client master from Excel, or load the demo firm.", action: <Button onClick={() => { loadDemoFirm(); toast.success("Demo firm loaded"); }}>Load demo firm</Button> }}
          toolbar={
            <DropdownMenu>
              <DropdownMenuTrigger asChild><Button size="sm" variant="outline" disabled={!sel.size}>Bulk actions ({sel.size})</Button></DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-60">
                <DropdownMenuItem onSelect={() => { void runAll(ids); toast.success("Running selected clients"); }}>Run reconciliation</DropdownMenuItem>
                <DropdownMenuItem onSelect={() => bulk({ active: true }, "Marked active")}>Mark active</DropdownMenuItem>
                <DropdownMenuItem onSelect={() => bulk({ active: false }, "Marked inactive")}>Mark inactive</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">Assign staff</DropdownMenuLabel>
                {users.map((u) => <DropdownMenuItem key={u.id} onSelect={() => bulk({ staff: u.name }, `Assigned to ${u.name}`)}>{u.name}</DropdownMenuItem>)}
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">Set data source</DropdownMenuLabel>
                {DATA_SOURCES.map((d) => <DropdownMenuItem key={d} onSelect={() => bulk({ dataSource: d }, `Data source set to ${d}`)}>{d}</DropdownMenuItem>)}
                {partner && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem className="text-destructive" onSelect={() => { if (confirm(`Delete ${ids.length} client(s) and all their data? This cannot be undone.`)) { ids.forEach((id) => deleteClientData(id, true)); setSel(new Set()); toast.success("Clients deleted"); } }}>Delete selected…</DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          }
        />
      </Panel>
      {editing && <ClientDialog value={editing.c} isNew={editing.isNew} existing={all} onClose={() => setEditing(null)} />}
      {importing && <ImportReview parsed={importing} onClose={() => setImporting(null)} />}
    </div>
  );
}

function ClientDialog({ value, isNew, existing, onClose }: { value: Client; isNew: boolean; existing: Client[]; onClose: () => void }) {
  const [c, setC] = useState(value);
  const [errors, setErrors] = useState<string[]>([]);
  const users = useApp((s) => s.users);
  const g = c.gstin ? validateGstin(c.gstin) : null;
  const set = (p: Partial<Client>) => setC({ ...c, ...p });
  const text = (k: keyof Client, label: ReactNodeLike, extra?: { placeholder?: string; maxLength?: number; mono?: boolean; type?: string }) => (
    <div className="space-y-1.5">
      <Label htmlFor={`f-${String(k)}`}>{label}</Label>
      <Input id={`f-${String(k)}`} type={extra?.type ?? "text"} className={extra?.mono ? "font-mono uppercase" : ""} maxLength={extra?.maxLength} placeholder={extra?.placeholder} value={String(c[k] ?? "")}
        onChange={(e) => set({ [k]: k === "gstin" ? e.target.value.toUpperCase() : e.target.value } as Partial<Client>)} />
    </div>
  );
  const toggle = (k: "apiEnabled" | "fetchReturns" | "fetchNotices" | "active", label: string) => (
    <label className="flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm">{label}<Switch checked={c[k]} onCheckedChange={(v) => set({ [k]: v } as Partial<Client>)} /></label>
  );
  const save = () => {
    const errs = validateClient(c as ClientInput, existing.filter((x) => x.id !== c.id).map((x) => x.gstin));
    setErrors(errs);
    if (errs.length) return;
    saveClient({ ...c, filing: c.frequency, state: c.state || c.gstin.slice(0, 2) }, isNew);
    toast.success("Client saved");
    onClose();
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isNew ? "Add client" : "Edit client"}</DialogTitle>
          <DialogDescription>Fields marked * are required. We never ask for the GST portal password — portal access is only through a GSP with the client's OTP.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          {text("name", "Client name *")}
          {text("tradeName", "Trade name")}
          <div className="space-y-1.5">
            {text("gstin", <Term k="GSTIN">GSTIN *</Term>, { maxLength: 15, mono: true, placeholder: "e.g. 24ABCDE1234F1Z6" })}
            {g && <p className={`text-xs ${g.valid ? "text-success" : "text-destructive"}`}>{g.valid ? "GSTIN is valid (format and check digit)." : g.reason}</p>}
          </div>
          {text("portalUsername", "GST portal username * (not the password)")}
          {text("mobile4", "Registered mobile (last 4 digits)", { maxLength: 4, placeholder: "e.g. 4421" })}
          {text("email", "Registered email", { type: "email" })}
          <div className="space-y-1.5">
            <Label htmlFor="f-freq">Return frequency</Label>
            <select id="f-freq" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={c.frequency} onChange={(e) => set({ frequency: e.target.value as Client["frequency"] })}>
              <option>Monthly</option><option>QRMP</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="f-fy">Financial year</Label>
            <select id="f-fy" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={c.fy} onChange={(e) => set({ fy: e.target.value })}>
              {["2023-24", "2024-25", "2025-26", "2026-27"].map((y) => <option key={y}>{y}</option>)}
            </select>
          </div>
          {text("tallyCompany", "Tally company name")}
          <div className="space-y-1.5">
            <Label htmlFor="f-staff">Assigned staff</Label>
            <select id="f-staff" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={c.staff} onChange={(e) => set({ staff: e.target.value })}>
              <option value="">(unassigned)</option>
              {users.map((u) => <option key={u.id} value={u.name}>{u.name} — {u.role}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="f-ds"><Term k="Data source">Data source</Term></Label>
            <select id="f-ds" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={c.dataSource} onChange={(e) => set({ dataSource: e.target.value as DataSource })}>
              {DATA_SOURCES.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          {text("apiValidTill", "API access valid till", { type: "date" })}
          {toggle("apiEnabled", "API access enabled (Manage API Access = Yes)")}
          {toggle("active", "Active")}
          {toggle("fetchReturns", "Fetch returns")}
          {toggle("fetchNotices", "Fetch notices")}
          <div className="sm:col-span-2">{text("remarks", "Remarks")}</div>
        </div>
        {errors.length > 0 && <ul className="list-disc rounded-md bg-destructive/10 p-3 pl-6 text-sm text-destructive">{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={save}>Save client</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
type ReactNodeLike = Parameters<typeof Label>[0]["children"];

function ImportReview({ parsed, onClose }: { parsed: ReturnType<typeof parseClientRows>; onClose: () => void }) {
  const ok = parsed.filter((p) => !p.errors.length);
  const save = () => {
    for (const p of ok) saveClient({ ...blank(), ...p.client, filing: p.client.frequency, state: p.client.gstin.slice(0, 2) }, true);
    toast.success(`${ok.length} client(s) imported`);
    onClose();
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>Review the import before saving</DialogTitle>
          <DialogDescription>{ok.length} row(s) are ready; {parsed.length - ok.length} have errors and will be skipped. Fix those rows in Excel and import again.</DialogDescription>
        </DialogHeader>
        <DataTable
          rows={parsed}
          rowKey={(p) => String(p.row)}
          exportName="client_import_review"
          empty={{ message: "No rows." }}
          rowClassName={(p) => (p.errors.length ? "bg-destructive/5" : "")}
          columns={[
            { key: "row", title: "Excel row", header: "Row", value: (p) => p.row, align: "right" },
            { key: "st", title: "Status", header: "Status", value: (p) => (p.errors.length ? "Error" : "Ready"), filter: true, cell: (p) => <StatusBadge status={p.errors.length ? "Failed" : "Matched"} label={p.errors.length ? "Error" : "Ready"} /> },
            { key: "name", title: "Client name", header: "Client", value: (p) => p.client.name },
            { key: "gstin", title: "GSTIN", header: "GSTIN", value: (p) => p.client.gstin, cell: (p) => <span className="font-mono text-xs">{p.client.gstin}</span> },
            { key: "user", title: "Portal username", header: "Portal username", value: (p) => p.client.portalUsername },
            { key: "ds", title: "Data source", header: "Data source", value: (p) => p.client.dataSource },
            { key: "err", title: "Errors", header: "Errors", value: (p) => p.errors.join("; "), cell: (p) => <span className="text-xs text-destructive">{p.errors.join("; ") || "—"}</span> },
          ]}
        />
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button disabled={!ok.length} onClick={save}>Save {ok.length} client(s)</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
