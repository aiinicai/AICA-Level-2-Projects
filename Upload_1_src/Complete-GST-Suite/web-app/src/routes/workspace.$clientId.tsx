import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { FileSpreadsheet, FileText, Loader2, Pencil, Play, Plus, RotateCcw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Kpi, Money, PageHeader, Panel, StatusBadge, Term } from "@/components/gst/common";
import { DataTable } from "@/components/gst/DataTable";
import { ConnectData, SupplierFollowUp } from "@/components/gst/WorkspaceExtra";
import { ComparisonPanel, InvoiceMatchPanel, ThreeWay, useComparisons } from "@/components/gst/ReconPanels";
import { NoticeDialog, blankNotice } from "@/components/gst/NoticeDialog";
import { getClientData, getClientFiles } from "@/lib/gst/demo";
import { fmtDate, fmtDateTime, inr, monthLabel } from "@/lib/gst/format";
import { HEADS, HEAD_LABEL, R_IDS, SOURCE_LABEL, drc03, gstr9, gstr9c, itcAtRisk, summarise, sumInv, totalTax, type DraftLine, type Gstr9cInputs, type Head } from "@/lib/gst/recon";
import { validateGstin } from "@/lib/gst/gstin";
import { sessionStatus } from "@/lib/gst/gsp";
import { daysLeft, noticeStatus } from "@/lib/gst/notices";
import { exportClientWorkbook } from "@/lib/exports";
import { LoadingPage } from "@/components/gst/common";
import { canSee, useHydrated, deleteUploadedFile, overridesFor, runClient, set9cInputs, setOverride, setReason, useApp, useClient, useDataVersion, type Run } from "@/lib/store";
import type { Client, Notice } from "@/lib/gst/demo";

const TABS = ["overview", "connect", "suppliers", "threeway", "r1", "r2", "r3", "r4", "r5", "r6", "matching", "gstr9", "gstr9c", "files", "activity", "notices"] as const;
type Tab = (typeof TABS)[number];

export const Route = createFileRoute("/workspace/$clientId")({
  validateSearch: (s: Record<string, unknown>): { tab: string } => ({ tab: TABS.includes(s["tab"] as Tab) ? (s["tab"] as string) : "overview" }),
  head: () => ({
    meta: [
      { title: "Client workspace · Complete GST Suite" },
      { name: "description", content: "Client GST workspace: reconciliation R1–R6, three-way view, invoice matching, GSTR-9/9C drafts, files and notices." },
    ],
  }),
  component: Workspace,
});

function Workspace() {
  const { clientId } = Route.useParams();
  const { tab } = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });
  const client = useClient(clientId);
  const progress = useApp((s) => s.progress[clientId]);
  useApp((s) => s.currentUserId);
  useDataVersion();
  const comps = useComparisons(clientId);
  const hydrated = useHydrated();

  if (!hydrated) return <LoadingPage />;
  if (!client || !canSee(clientId)) {
    return (
      <div className="py-16 text-center">
        <p className="text-muted-foreground">{client ? "This client is not assigned to you." : "This client was not found. Load the demo firm or add the client first."}</p>
        <Button asChild className="mt-4"><Link to="/clients">Go to clients</Link></Button>
      </div>
    );
  }
  const running = progress === "running";
  const outer = ["threeway", "r1", "r2", "r3", "r4", "r5", "r6"].includes(tab) ? "recon" : tab;
  return (
    <div>
      <PageHeader
        title={client.name}
        subtitle={<span className="flex flex-wrap items-center gap-2"><span className="font-mono">{client.gstin}</span><StatusBadge status="neutral" label={`Data source: ${client.dataSource}`} />{!client.active && <StatusBadge status="neutral" label="Inactive" />}<span className="text-xs">Staff: {client.staff || "unassigned"}</span></span>}
        actions={
          <>
            <Button variant="outline" onClick={() => void exportClientWorkbook(clientId)}><FileSpreadsheet className="mr-2 h-4 w-4" /> Excel workbook</Button>
            <Button variant="outline" asChild><Link to="/print/$clientId" params={{ clientId }} target="_blank"><FileText className="mr-2 h-4 w-4" /> PDF summary</Link></Button>
            <Button onClick={() => void runClient(clientId).then((r) => (r.status === "Failed" ? toast.error(r.error ?? "Run failed") : toast.success(r.message ?? "Done")))} disabled={running}>
              {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />} Run reconciliation
            </Button>
          </>
        }
      />
      <Tabs value={outer} onValueChange={(v) => navigate({ search: { tab: v === "recon" ? "threeway" : v } })}>
        <div className="overflow-x-auto">
          <TabsList className="h-auto flex-nowrap">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="connect">Connect &amp; Data</TabsTrigger>
            <TabsTrigger value="recon">Reconciliation</TabsTrigger>
            <TabsTrigger value="matching">Invoice Matching</TabsTrigger>
            <TabsTrigger value="suppliers">Supplier Follow-up</TabsTrigger>
            <TabsTrigger value="gstr9">GSTR-9</TabsTrigger>
            <TabsTrigger value="gstr9c">GSTR-9C</TabsTrigger>
            <TabsTrigger value="notices">Notices</TabsTrigger>
            <TabsTrigger value="files">Files</TabsTrigger>
            <TabsTrigger value="activity">Activity</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="overview" className="mt-6"><Overview client={client} /></TabsContent>
        <TabsContent value="connect" className="mt-6"><ConnectData client={client} /></TabsContent>
        <TabsContent value="recon" className="mt-6">
          <Tabs value={tab} onValueChange={(v) => navigate({ search: { tab: v } })}>
            <TabsList>
              <TabsTrigger value="threeway">3-way view</TabsTrigger>
              {comps.map((c) => <TabsTrigger key={c.id} value={c.id.toLowerCase()}>{c.id}{c.rows.some((r) => r.status === "Difference") && <span className="ml-1 h-1.5 w-1.5 rounded-full bg-destructive" aria-label="has differences" />}</TabsTrigger>)}
            </TabsList>
            <TabsContent value="threeway" className="mt-6"><ThreeWay clientId={clientId} /></TabsContent>
            {comps.map((c) => <TabsContent key={c.id} value={c.id.toLowerCase()} className="mt-6"><ComparisonPanel clientId={clientId} comp={c} /></TabsContent>)}
          </Tabs>
        </TabsContent>
        <TabsContent value="matching" className="mt-6"><InvoiceMatchPanel clientId={clientId} /></TabsContent>
        <TabsContent value="suppliers" className="mt-6"><SupplierFollowUp client={client} /></TabsContent>
        <TabsContent value="gstr9" className="mt-6"><Gstr9Tab clientId={clientId} /></TabsContent>
        <TabsContent value="gstr9c" className="mt-6"><Gstr9cTab clientId={clientId} /></TabsContent>
        <TabsContent value="notices" className="mt-6"><ClientNotices client={client} /></TabsContent>
        <TabsContent value="files" className="mt-6"><Files clientId={clientId} /></TabsContent>
        <TabsContent value="activity" className="mt-6"><ClientActivity clientId={clientId} /></TabsContent>
      </Tabs>
    </div>
  );
}

function Overview({ client }: { client: Client }) {
  const clientId = client.id;
  const cd = getClientData(clientId);
  const runs = useApp((s) => s.runs).filter((r) => r.clientId === clientId);
  const tol = useApp((s) => s.prefs.tolerance);
  const session = useApp((s) => s.sessions[clientId]);
  const comps = useComparisons(clientId);
  const sum = summarise(clientId, tol);
  const risk = itcAtRisk(clientId, tol);
  const drc = drc03(clientId);
  const sales = sumInv(cd.sales);
  const itc = sumInv(cd.purchases);
  const g = validateGstin(client.gstin);
  const [cmp, setCmp] = useState<Set<string>>(new Set());
  const picked = runs.filter((r) => cmp.has(r.id));

  return (
    <div className="space-y-6">
      {sum.partialMonths.length > 0 && (
        <div className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning-foreground">
          <b>Partial data:</b> missing {Object.entries(sum.missing).filter(([, m]) => m.length).map(([k, m]) => `${k.toUpperCase().replace("GSTR", "GSTR-")} ${m.map(monthLabel).join(", ")}`).join("; ")}. Those months are flagged amber. <Link to="/workspace/$clientId" params={{ clientId }} search={{ tab: "connect" }} className="underline">Upload the files</Link>.
        </div>
      )}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <Kpi label={<Term k="Taxable value">Sales — taxable value</Term>} value={<Money value={sales.taxable} rows={cd.sales} title="Sales register — FY 2025-26" />} hint={`${cd.sales.length} invoices in books`} />
        <Kpi label="Output tax (books)" value={<Money value={totalTax(sales)} rows={cd.sales} title="Sales register — FY 2025-26" />} hint="IGST + CGST + SGST + Cess" />
        <Kpi label={<Term k="ITC">ITC in books</Term>} value={<Money value={totalTax(itc)} rows={cd.purchases} title="Purchase register — FY 2025-26" />} hint={`${cd.purchases.length} purchase invoices`} />
        <Kpi label={<Term k="ITC at risk" />} value={<Money value={risk.amount} rows={risk.invoices} title="ITC at risk" subtitle="Only in books, or value differs from GSTR-2B" />} tone={risk.amount ? "warning" : "success"} hint={`${risk.invoices.length} invoice(s)`} />
        <Kpi label={<Term k="DRC-03">DRC-03 payable</Term>} value={<Money value={drc.total} rows={cd.sales.filter((s) => drc.months.some((m) => m.month === s.month))} title="Months with tax short-paid in GSTR-3B" />} tone={drc.total ? "danger" : "success"} hint={drc.total ? `+ interest u/s 50 ≈ ${inr(drc.interestTotal)}` : "Nothing short-paid"} />
        <Kpi label="Months with differences" value={sum.differences} tone={sum.differences ? "danger" : "success"} hint={sum.pending ? `${sum.pending} month(s) partial data` : "across R1–R6"} />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Panel title="Client details">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="text-muted-foreground"><Term k="GSTIN" /></dt><dd className="font-mono">{client.gstin} {g.valid && <StatusBadge status="Matched" label="Valid" />}</dd>
            <dt className="text-muted-foreground">Trade name</dt><dd>{client.tradeName || "—"}</dd>
            <dt className="text-muted-foreground">Portal username</dt><dd>{client.portalUsername || "—"}</dd>
            <dt className="text-muted-foreground">Registered mobile</dt><dd>{client.mobile4 ? `•••••• ${client.mobile4}` : "—"}</dd>
            <dt className="text-muted-foreground">Email</dt><dd>{client.email || "—"}</dd>
            <dt className="text-muted-foreground">Frequency</dt><dd>{client.frequency}</dd>
            <dt className="text-muted-foreground">Tally company</dt><dd>{client.tallyCompany || "—"}</dd>
            <dt className="text-muted-foreground">API access</dt><dd>{client.apiEnabled ? `Enabled${client.apiValidTill ? ` till ${fmtDate(client.apiValidTill)}` : ""}` : "Not enabled"}</dd>
            <dt className="text-muted-foreground"><Term k="GSP">GSP session</Term></dt><dd><StatusBadge status={sessionStatus(session) === "Connected" ? "Matched" : sessionStatus(session) === "Expired" ? "Overdue" : "neutral"} label={sessionStatus(session)} />{session && <span className="ml-2 text-xs text-muted-foreground">till {fmtDateTime(session.expiry)}</span>}</dd>
            <dt className="text-muted-foreground">Assigned staff</dt><dd>{client.staff || "—"}</dd>
          </dl>
          {client.remarks && <p className="mt-4 rounded-md bg-muted p-3 text-xs text-muted-foreground">{client.remarks}</p>}
        </Panel>
        <Panel title="Reconciliation summary" className="xl:col-span-2">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr className="border-b"><th className="py-2 pr-2 font-medium">Check</th><th className="py-2 pr-2 font-medium">What it compares</th><th className="py-2 pr-2 text-right font-medium">Year difference</th><th className="py-2 pr-2 font-medium">Months</th><th className="py-2 font-medium">Status</th></tr>
            </thead>
            <tbody>
              {comps.map((c) => {
                const stt = sum.byR[c.id] ?? "Matched";
                return (
                  <tr key={c.id} className="border-b last:border-0">
                    <td className="py-2 pr-2 font-medium"><Link to="/workspace/$clientId" params={{ clientId }} search={{ tab: c.id.toLowerCase() }} className="text-primary hover:underline">{c.id}</Link></td>
                    <td className="py-2 pr-2"><Term k={c.id}>{c.title}</Term></td>
                    <td className={`py-2 pr-2 text-right tabular-nums ${stt === "Difference" ? "text-destructive" : ""}`}>{inr(totalTax(c.total.diff))}</td>
                    <td className="py-2 pr-2 text-xs text-muted-foreground">{sum.diffMonths[c.id]?.map(monthLabel).join(", ") || "—"}</td>
                    <td className="py-2"><Link to="/workspace/$clientId" params={{ clientId }} search={{ tab: c.id.toLowerCase() }}><StatusBadge status={stt} /></Link></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>
      </div>

      <Panel title="Run history" actions={<Button size="sm" variant="outline" disabled={picked.length !== 2} onClick={() => setCmp(new Set())}>{picked.length === 2 ? "Clear comparison" : "Tick two runs to compare"}</Button>}>
        <DataTable
          rows={runs}
          rowKey={(r) => r.id}
          exportName={`${clientId}_run_history`}
          selection={{ selected: cmp, onChange: (s) => setCmp(new Set([...s].slice(-2))) }}
          maxHeight="40vh"
          empty={{ message: "Not run yet — click “Run reconciliation” above, or “Run all clients” on the dashboard." }}
          columns={[
            { key: "at", title: "When", header: "When", value: (r) => r.at, cell: (r) => fmtDateTime(r.at) },
            { key: "by", title: "By", header: "By", value: (r) => r.by },
            { key: "route", title: "Data used", header: "Data used", value: (r) => r.route ?? "—" },
            { key: "status", title: "Result", header: "Result", value: (r) => r.status, cell: (r) => <StatusBadge status={r.status} /> },
            { key: "diff", title: "Differences", header: "Differences", value: (r) => r.summary?.differences ?? null, align: "right" },
            { key: "risk", title: "ITC at risk", header: "ITC at risk", value: (r) => r.summary?.itcAtRisk ?? null, money: true, align: "right" },
            { key: "msg", title: "Message", header: "Message", value: (r) => r.error ?? r.message ?? "", cell: (r) => <span className={`text-xs ${r.error ? "text-destructive" : "text-muted-foreground"}`}>{r.error ?? r.message}</span> },
          ]}
        />
        {picked.length === 2 && <RunCompare a={picked[1]!} b={picked[0]!} />}
      </Panel>
    </div>
  );
}

function RunCompare({ a, b }: { a: Run; b: Run }) {
  const rows: [string, number | undefined, number | undefined][] = [
    ...R_IDS.map((k): [string, number | undefined, number | undefined] => [`${k} year difference`, a.summary?.yearDiff[k], b.summary?.yearDiff[k]]),
    ["Tax difference 3B vs books", a.summary?.netTaxDiff, b.summary?.netTaxDiff],
    ["ITC at risk", a.summary?.itcAtRisk, b.summary?.itcAtRisk],
    ["DRC-03 payable", a.summary?.drc03, b.summary?.drc03],
    ["Months with differences", a.summary?.differences, b.summary?.differences],
  ];
  return (
    <div className="mt-4 rounded-md border p-3">
      <div className="mb-2 text-sm font-medium">Comparing {fmtDateTime(a.at)} → {fmtDateTime(b.at)}</div>
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-muted-foreground"><tr className="border-b"><th className="py-1 pr-2 font-medium">Item</th><th className="py-1 pr-2 text-right font-medium">Earlier</th><th className="py-1 pr-2 text-right font-medium">Later</th><th className="py-1 text-right font-medium">Change</th></tr></thead>
        <tbody>
          {rows.map(([k, x, y]) => {
            const ch = (y ?? 0) - (x ?? 0);
            const count = k.startsWith("Months");
            return (
              <tr key={k} className="border-b last:border-0">
                <td className="py-1 pr-2">{k}</td>
                <td className="py-1 pr-2 text-right tabular-nums">{x === undefined ? "—" : count ? x : inr(x)}</td>
                <td className="py-1 pr-2 text-right tabular-nums">{y === undefined ? "—" : count ? y : inr(y)}</td>
                <td className={`py-1 text-right tabular-nums ${Math.abs(ch) > 1 ? "font-medium text-destructive" : "text-muted-foreground"}`}>{count ? ch : inr(ch)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Gstr9Tab({ clientId }: { clientId: string }) {
  const all = useApp((s) => s.draftOverrides);
  const ov = overridesFor(all, clientId, "GSTR-9");
  return <Draft clientId={clientId} form="GSTR-9" lines={gstr9(clientId, ov)} title="GSTR-9 draft (annual return)" />;
}

function Gstr9cTab({ clientId }: { clientId: string }) {
  const all = useApp((s) => s.draftOverrides);
  const inputs = useApp((s) => s.gstr9cInputs[clientId]) ?? {};
  const lines = gstr9c(clientId, inputs, overridesFor(all, clientId, "GSTR-9C"), overridesFor(all, clientId, "GSTR-9"));
  const fields: [keyof Gstr9cInputs, string, string][] = [
    ["auditedTurnover", "Turnover as per audited financial statements", "Blank = GSTR-9 5N"],
    ["unbilled", "Unbilled revenue adjustment", "Default 0"],
    ["otherIncome", "Other income not part of GST turnover", "Default 0"],
    ["itcAudited", "ITC as per audited financial statements", "Blank = GSTR-9 7J"],
  ];
  return (
    <div className="space-y-6">
      <Panel title="Inputs from audited financial statements">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {fields.map(([k, label, hint]) => (
            <label key={k} className="space-y-1 text-sm">
              <span className="font-medium">{label}</span>
              <Input type="number" inputMode="decimal" className="text-right tabular-nums" placeholder={hint} value={inputs[k] ?? ""} onChange={(e) => set9cInputs(clientId, { ...inputs, [k]: e.target.value === "" ? undefined : Number(e.target.value) })} />
            </label>
          ))}
        </div>
      </Panel>
      <Draft clientId={clientId} form="GSTR-9C" lines={lines} title="GSTR-9C draft (reconciliation statement)" />
    </div>
  );
}

function Draft({ clientId, form, lines, title }: { clientId: string; form: "GSTR-9" | "GSTR-9C"; lines: DraftLine[]; title: string }) {
  const tol = useApp((s) => s.prefs.tolerance);
  const reasons = useApp((s) => s.draftReasons);
  const [editing, setEditing] = useState<string | null>(null);
  const cell = (l: DraftLine, h: Head) => {
    if (!l.heads.includes(h)) return <span className="text-muted-foreground">—</span>;
    const over = l.overridden.includes(h);
    if (editing === l.id)
      return <Input type="number" defaultValue={l.v[h]} aria-label={`${l.label} ${HEAD_LABEL[h]}`} className="h-8 w-28 text-right tabular-nums" onBlur={(e) => { const v = Number(e.target.value); if (Number.isFinite(v) && v !== l.v[h]) setOverride(clientId, form, `${l.id}.${h}`, v); }} />;
    return <span className={over ? "rounded bg-warning/20 px-1" : ""} title={over ? "Manual override (logged in Activity)" : undefined}><Money value={l.v[h]} rows={l.rows} title={`${form} ${l.label}`} /></span>;
  };
  return (
    <Panel title={<Term k={form}>{title}</Term>} actions={<span className="text-xs text-muted-foreground">Draft for review — not filed · <span className="rounded bg-warning/20 px-1">highlighted</span> = manual override</span>}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1100px] text-sm">
          <thead className="text-left text-xs text-muted-foreground">
            <tr className="border-b">
              <th className="py-2 pr-2 font-medium">Table</th>
              <th className="py-2 pr-2 font-medium">Particulars</th>
              {HEADS.map((h) => <th key={h} className="py-2 pr-2 text-right font-medium">{h === "taxable" ? "Taxable / Amount" : <Term k={HEAD_LABEL[h]}>{HEAD_LABEL[h]}</Term>}</th>)}
              <th className="py-2 pr-2 font-medium">Source</th>
              <th className="py-2 pr-2 font-medium">Note / reason</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {lines.map((l) => {
              const amount = l.heads.length === 1 && l.heads[0] === "taxable" ? l.v.taxable : totalTax(l.v);
              const unrec = l.diff && Math.abs(amount) > tol;
              const rk = `${clientId}|${form}:${l.id}`;
              return (
                <tr key={l.id} className={`border-b align-top last:border-0 ${unrec ? "bg-destructive/5" : ""}`}>
                  <td className="whitespace-nowrap py-2 pr-2"><Term k={l.id.split("-")[0]!}>{l.id.split("-")[0]}</Term></td>
                  <td className="py-2 pr-2">{l.label}</td>
                  {HEADS.map((h) => <td key={h} className={`whitespace-nowrap py-2 pr-2 text-right ${unrec && Math.abs(l.v[h]) > tol ? "font-medium text-destructive" : ""}`}>{cell(l, h)}</td>)}
                  <td className="whitespace-nowrap py-2 pr-2 text-xs text-muted-foreground">{l.overridden.length ? "Manual override" : SOURCE_LABEL[l.source]}</td>
                  <td className="min-w-56 py-2 pr-2 text-xs text-muted-foreground">
                    {l.note && <div>{l.note}</div>}
                    {l.diff && (unrec ? <Input className="mt-1 h-8 text-xs" placeholder="Reason for this difference (required before filing)" defaultValue={reasons[rk] ?? ""} onBlur={(e) => e.target.value !== (reasons[rk] ?? "") && setReason(clientId, `${form}:${l.id}`, e.target.value)} /> : !l.note ? "Reconciled." : null)}
                  </td>
                  <td className="whitespace-nowrap py-2 text-right">
                    <Button size="icon" variant="ghost" className="h-7 w-7" aria-label={`Edit ${l.label}`} onClick={() => setEditing(editing === l.id ? null : l.id)}><Pencil className="h-3.5 w-3.5" /></Button>
                    {l.overridden.length > 0 && <Button size="icon" variant="ghost" className="h-7 w-7" aria-label={`Reset ${l.label}`} onClick={() => l.overridden.forEach((h) => setOverride(clientId, form, `${l.id}.${h}`, undefined))}><RotateCcw className="h-3.5 w-3.5" /></Button>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function Files({ clientId }: { clientId: string }) {
  useDataVersion();
  const files = getClientFiles(clientId);
  return (
    <Panel title="Files for this client" actions={<span className="text-xs text-muted-foreground">Stored privately for this firm · client · FY 2025-26</span>}>
      <DataTable
        rows={files}
        rowKey={(f) => f.id}
        exportName={`${clientId}_files`}
        empty={{ message: "No files yet.", action: <Button asChild size="sm"><Link to="/workspace/$clientId" params={{ clientId }} search={{ tab: "connect" }}>Upload files in Connect &amp; Data</Link></Button> }}
        columns={[
          { key: "name", title: "File", header: "File", value: (f) => f.name, cell: (f) => <span className="font-mono text-xs">{f.name}</span> },
          { key: "kind", title: "Detected type", header: "Detected type", value: (f) => f.kind, filter: true },
          { key: "period", title: "Period", header: "Period", value: (f) => (/^\d{4}-\d{2}$/.test(f.period) ? monthLabel(f.period) : f.period) },
          { key: "rows", title: "Rows", header: "Rows", value: (f) => f.rows, align: "right" },
          { key: "status", title: "Status", header: "Status", value: (f) => f.status, filter: true, cell: (f) => <span><StatusBadge status={f.status} label={f.status === "Missing" ? "Not uploaded" : f.status} />{f.message && <div className="mt-0.5 max-w-72 text-[11px] text-muted-foreground">{f.message}</div>}</span> },
          { key: "at", title: "Uploaded", header: "Uploaded", value: (f) => f.at ?? "", cell: (f) => <span className="text-xs text-muted-foreground">{f.at ? `${fmtDateTime(f.at)} · ${f.by}` : f.uploaded ? "" : "seeded demo file"}</span> },
          { key: "del", title: "", header: "", value: () => "", noExport: true, cell: (f) => (f.uploaded ? <Button size="icon" variant="ghost" className="h-7 w-7" aria-label={`Remove ${f.name} from the list`} onClick={() => deleteUploadedFile(clientId, f.id)}><Trash2 className="h-3.5 w-3.5" /></Button> : null) },
        ]}
      />
    </Panel>
  );
}

function ClientActivity({ clientId }: { clientId: string }) {
  const items = useApp((s) => s.activity).filter((a) => a.clientId === clientId);
  return (
    <Panel title="Activity for this client">
      <DataTable rows={items} rowKey={(a) => a.id} exportName={`${clientId}_activity`} empty={{ message: "No activity yet. Runs, uploads, GSP connections, exports and notice changes appear here." }}
        columns={[
          { key: "at", title: "When", header: "When", value: (a) => a.at, cell: (a) => <span className="whitespace-nowrap text-xs text-muted-foreground">{fmtDateTime(a.at)}</span> },
          { key: "by", title: "Who", header: "Who", value: (a) => a.by, filter: true },
          { key: "action", title: "What happened", header: "What happened", value: (a) => a.action },
        ]} />
    </Panel>
  );
}

function ClientNotices({ client }: { client: Client }) {
  const soon = useApp((s) => s.prefs.reminderDays);
  const notices = useApp((s) => s.notices).filter((n) => n.clientId === client.id);
  const [editing, setEditing] = useState<Notice | null>(null);
  return (
    <Panel title="Notices for this client" actions={<Button size="sm" onClick={() => setEditing(blankNotice(client))}><Plus className="mr-1.5 h-3.5 w-3.5" /> Add notice</Button>}>
      <DataTable
        rows={[...notices].sort((a, b) => a.due.localeCompare(b.due))}
        rowKey={(n) => n.id}
        exportName={`${client.id}_notices`}
        onRowClick={setEditing}
        empty={{ message: "No notices for this client.", action: <Button size="sm" onClick={() => setEditing(blankNotice(client))}>Add notice</Button> }}
        columns={[
          { key: "chip", title: "Status", header: "Status", value: (n) => noticeStatus(n, new Date(), soon), filter: true, cell: (n) => <StatusBadge status={noticeStatus(n, new Date(), soon)} /> },
          { key: "form", title: "Form", header: "Form", value: (n) => n.form, cell: (n) => <Term k={n.form} /> },
          { key: "nature", title: "Nature", header: "Nature", value: (n) => n.subject, cell: (n) => <span>{n.subject}<div className="font-mono text-[11px] text-muted-foreground">{n.ref}</div></span> },
          { key: "due", title: "Reply due", header: "Reply due", value: (n) => n.due, cell: (n) => <span className="whitespace-nowrap">{fmtDate(n.due)}{!n.replied && <div className="text-[11px] text-muted-foreground">{daysLeft(n) < 0 ? `${-daysLeft(n)} days overdue` : `${daysLeft(n)} days left`}</div>}</span> },
          { key: "pr", title: "Priority", header: "Priority", value: (n) => n.priority },
          { key: "action", title: "Action required", header: "Action required", value: (n) => n.action, cell: (n) => <span className="text-xs">{n.action}</span> },
          { key: "assigned", title: "Assigned to", header: "Assigned to", value: (n) => n.assignedTo },
          { key: "status", title: "Internal status", header: "Internal status", value: (n) => n.status, filter: true },
        ]}
      />
      {editing && <NoticeDialog value={editing} onClose={() => setEditing(null)} />}
    </Panel>
  );
}
