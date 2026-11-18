import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Bell, Building2, Loader2, Play, Rocket, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Kpi, LoadingPage, Money, PageHeader, Panel, StatusBadge, Term } from "@/components/gst/common";
import { DataTable, type Column } from "@/components/gst/DataTable";
import { daysBetween, fmtDate, fmtDateTime, inr, monthLabel } from "@/lib/gst/format";
import { R_IDS, itcAtRisk } from "@/lib/gst/recon";
import { decideRoute } from "@/lib/gst/gsp";
import { noticeStatus } from "@/lib/gst/notices";
import { checkNotices, latestRun, loadDemoFirm, runAll, sessionOf, useApp, useClients, useHydrated, type Run } from "@/lib/store";
import type { Client } from "@/lib/gst/demo";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — Complete GST Suite" },
      { name: "description", content: "Firm-wide view of GST reconciliation status, ITC at risk, DRC-03 payable and upcoming notice deadlines." },
      { property: "og:title", content: "Dashboard — Complete GST Suite" },
      { property: "og:description", content: "Firm-wide view of GST reconciliation status and notice deadlines." },
    ],
  }),
  component: Dashboard,
});

interface Row {
  c: Client;
  run?: Run | undefined;
  route: string;
  status: string;
  open: number;
  overdue: number;
}

function Dashboard() {
  const navigate = useNavigate();
  const clients = useClients();
  const runs = useApp((s) => s.runs);
  const progress = useApp((s) => s.progress);
  const notices = useApp((s) => s.notices);
  const firm = useApp((s) => s.firm);
  const soon = useApp((s) => s.prefs.reminderDays);
  const tol = useApp((s) => s.prefs.tolerance);
  useApp((s) => s.sessions);
  const running = Object.values(progress).some((p) => p === "running" || p === "queued");
  const hydrated = useHydrated();

  if (!hydrated) return <LoadingPage />;
  if (!clients.length) {
    return (
      <div className="mx-auto max-w-2xl py-16 text-center">
        <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-primary"><Building2 className="h-7 w-7" /></div>
        <h1 className="text-2xl font-semibold">Welcome to Complete GST Suite</h1>
        <p className="mx-auto mt-3 max-w-lg text-muted-foreground">Reconcile every client's GST returns with their books, draft GSTR-9 and GSTR-9C, and never miss a notice deadline. Start with the demo firm — it takes under two minutes.</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button size="lg" onClick={() => { loadDemoFirm(); toast.success("Demo firm loaded — 4 clients and 6 notices. Click “Run all clients”."); }}><Sparkles className="mr-2 h-4 w-4" /> Load demo firm</Button>
          <Button size="lg" variant="outline" asChild><Link to="/setup"><Rocket className="mr-2 h-4 w-4" /> Guided setup</Link></Button>
          <Button size="lg" variant="outline" asChild><Link to="/clients">Add clients</Link></Button>
        </div>
      </div>
    );
  }

  const ids = new Set(clients.map((c) => c.id));
  const myNotices = notices.filter((n) => ids.has(n.clientId));
  const rows: Row[] = clients.map((c) => {
    const run = latestRun(runs, c.id);
    const cn_ = myNotices.filter((n) => n.clientId === c.id);
    const d = decideRoute(c, sessionOf(c.id));
    return {
      c,
      run,
      route: run?.route ?? d.route,
      status: !c.active ? "Inactive" : progress[c.id] === "running" ? "Running" : !run ? "Not run" : run.status === "Failed" ? "Failed" : run.summary?.partialMonths.length ? "Partial data" : run.summary?.differences ? "Difference" : "Matched",
      open: cn_.filter((n) => ["Open", "Due soon", "Overdue"].includes(noticeStatus(n, new Date(), soon))).length,
      overdue: cn_.filter((n) => noticeStatus(n, new Date(), soon) === "Overdue").length,
    };
  });
  const active = clients.filter((c) => c.active);
  const done = rows.filter((r) => r.c.active && r.run?.summary);
  const sumOf = (f: (r: Row) => number) => done.reduce((s, r) => s + f(r), 0);
  const reconciled = done.filter((r) => r.run!.summary!.reconciled).length;
  const overdue = myNotices.filter((n) => noticeStatus(n, new Date(), soon) === "Overdue");
  const dueSoon = myNotices.filter((n) => noticeStatus(n, new Date(), soon) === "Due soon");
  const riskRows = done.flatMap((r) => itcAtRisk(r.c.id, tol).invoices);
  const anyRun = done.length > 0;

  const yearCell = (r: Row, k: string) => {
    const s = r.run?.summary;
    if (!s) return <span className="text-xs text-muted-foreground">—</span>;
    const bad = s.byR[k] === "Difference";
    const partial = s.byR[k] === "Partial data";
    return (
      <Link to="/workspace/$clientId" params={{ clientId: r.c.id }} search={{ tab: k.toLowerCase() }} onClick={(e) => e.stopPropagation()}
        className={cn("inline-block rounded px-1.5 py-0.5 text-xs tabular-nums", bad ? "bg-destructive/10 font-medium text-destructive" : partial ? "bg-warning/15 text-warning-foreground" : "bg-success/10 text-success")}
        title={bad ? `Difference in ${s.diffMonths[k]?.map(monthLabel).join(", ")}` : partial ? "Partial data — a return is missing" : "All months matched"}>
        {bad ? inr(s.yearDiff[k] ?? 0) : partial ? "Partial" : "OK"}
      </Link>
    );
  };

  const cols: Column<Row>[] = [
    { key: "client", title: "Client", header: "Client", value: (r) => r.c.name, cell: (r) => (
      <div><Link to="/workspace/$clientId" params={{ clientId: r.c.id }} search={{ tab: "overview" }} className="font-medium hover:text-primary hover:underline" onClick={(e) => e.stopPropagation()}>{r.c.name}</Link>
        <div className="font-mono text-[11px] text-muted-foreground">{r.c.gstin}</div></div>) },
    { key: "gstin", title: "GSTIN", header: <Term k="GSTIN" />, value: (r) => r.c.gstin, cell: () => null, className: "hidden" },
    { key: "staff", title: "Staff", header: "Staff", value: (r) => r.c.staff, filter: true },
    { key: "source", title: "Data source used", header: <Term k="Data source">Data source</Term>, value: (r) => r.route, filter: true, cell: (r) => <span className="text-xs">{r.route}<div className="text-muted-foreground">setting: {r.c.dataSource}</div></span> },
    { key: "status", title: "Status", header: "Status", value: (r) => r.status, filter: true, cell: (r) => progress[r.c.id] === "running" || progress[r.c.id] === "queued"
      ? <div className="w-28"><StatusBadge status="running" label={progress[r.c.id] === "running" ? "Checking…" : "Queued"} /><Progress className="mt-1 h-1" value={progress[r.c.id] === "running" ? 60 : 5} /></div>
      : <span title={r.run?.error ?? r.run?.message}><StatusBadge status={r.status} /></span> },
    ...R_IDS.map((k): Column<Row> => ({ key: k, title: `${k} year difference`, header: <Term k={k} />, value: (r) => r.run?.summary?.yearDiff[k] ?? null, money: true, align: "right", cell: (r) => yearCell(r, k) })),
    { key: "itc", title: "ITC at risk", header: <Term k="ITC at risk" />, value: (r) => r.run?.summary?.itcAtRisk ?? null, money: true, align: "right", cell: (r) => r.run?.summary ? <Money value={r.run.summary.itcAtRisk} rows={itcAtRisk(r.c.id, tol).invoices} title={`${r.c.name} — ITC at risk`} /> : "—" },
    { key: "drc", title: "DRC-03 payable", header: <Term k="DRC-03">DRC-03</Term>, value: (r) => r.run?.summary?.drc03 ?? null, money: true, align: "right", cell: (r) => r.run?.summary ? <Link to="/workspace/$clientId" params={{ clientId: r.c.id }} search={{ tab: "gstr9" }} className="hover:underline" onClick={(e) => e.stopPropagation()}>{inr(r.run.summary.drc03)}</Link> : "—" },
    { key: "notices", title: "Open notices", header: "Notices", value: (r) => r.open, align: "right", cell: (r) => <Link to="/workspace/$clientId" params={{ clientId: r.c.id }} search={{ tab: "notices" }} onClick={(e) => e.stopPropagation()} className="hover:underline">{r.open}{r.overdue ? <span className="ml-1 text-destructive">({r.overdue} overdue)</span> : null}</Link> },
    { key: "last", title: "Last run", header: "Last run", value: (r) => r.run?.at ?? "", cell: (r) => <span className="whitespace-nowrap text-xs text-muted-foreground">{r.run ? fmtDateTime(r.run.at) : "Not run yet"}</span> },
    { key: "open", title: "", header: "", value: () => "", noExport: true, cell: (r) => <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); navigate({ to: "/workspace/$clientId", params: { clientId: r.c.id }, search: { tab: "overview" } }); }}>Open</Button> },
  ];

  return (
    <div>
      <PageHeader
        title={`Good day${firm ? ", " + firm.partner.replace(/^CA\s+/, "").split(" ")[0] : ""}`}
        subtitle={`${firm?.name ?? "Your firm"} · FY 2025-26 · ${active.length} active client(s)`}
        actions={
          <>
            <Button variant="outline" disabled={running} onClick={() => { void checkNotices().then((r) => toast.success(`Notice check finished — ${r.added} new notice(s)`, { description: r.skipped.length ? `Skipped: ${r.skipped.join("; ")}` : undefined })); }}>
              <Bell className="mr-2 h-4 w-4" /> Check notices only
            </Button>
            <Button onClick={() => { void runAll().then(() => toast.success("Run finished — see the run log for details")); }} disabled={running}>
              {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}{running ? "Running…" : "Run all clients"}
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
        <Kpi label="Active clients" value={active.length} hint={`${clients.length - active.length} inactive`} onClick={() => navigate({ to: "/clients" })} />
        <Kpi label="Fully reconciled" value={anyRun ? `${reconciled} / ${active.length}` : "—"} hint={anyRun ? "all six checks matched" : "Run all clients to check"} tone={anyRun ? (reconciled === active.length ? "success" : undefined) : undefined} />
        <Kpi label={<Term k="R2">Tax diff (3B vs books)</Term>} value={anyRun ? inr(sumOf((r) => r.run!.summary!.netTaxDiff)) : "—"} hint="months flagged in R2" tone={sumOf((r) => r.run!.summary!.netTaxDiff) ? "danger" : undefined} />
        <Kpi label={<Term k="ITC at risk" />} value={anyRun ? <Money value={sumOf((r) => r.run!.summary!.itcAtRisk)} rows={riskRows} title="ITC at risk — all clients" subtitle="Only in books, or value differs from GSTR-2B" /> : "—"} hint="supplier follow-up needed" tone={anyRun && sumOf((r) => r.run!.summary!.itcAtRisk) ? "warning" : undefined} />
        <Kpi label={<Term k="DRC-03">DRC-03 payable</Term>} value={anyRun ? inr(sumOf((r) => r.run!.summary!.drc03)) : "—"} hint={anyRun ? `+ interest ≈ ${inr(sumOf((r) => r.run!.summary!.interest))}` : "books liability > 3B"} tone={sumOf((r) => r.run!.summary!.drc03) ? "danger" : undefined} />
        <Kpi label="Notices overdue" value={overdue.length} hint="reply date passed" tone={overdue.length ? "danger" : "success"} onClick={() => navigate({ to: "/notices", search: { view: "list", status: "Overdue" } })} />
        <Kpi label={`Notices due in ${soon} days`} value={dueSoon.length} hint="reply now" tone={dueSoon.length ? "warning" : undefined} onClick={() => navigate({ to: "/notices", search: { view: "list", status: "Due soon" } })} />
      </div>

      <div className="mt-6 grid gap-6 2xl:grid-cols-4">
        <Panel title="Clients — reconciliation status" className="2xl:col-span-3">
          <DataTable
            rows={rows}
            columns={cols.filter((c) => c.key !== "gstin")}
            rowKey={(r) => r.c.id}
            exportName="firm_dashboard_FY2025-26"
            empty={{ message: "No clients yet." }}
            onRowClick={(r) => navigate({ to: "/workspace/$clientId", params: { clientId: r.c.id }, search: { tab: "overview" } })}
            rowClassName={(r) => (!r.c.active ? "opacity-60" : "")}
          />
          <p className="mt-2 text-xs text-muted-foreground">R1–R6 cells show the year's net tax difference (side A − side B); red means at least one month differs. Click any cell to open the month-wise grid.</p>
        </Panel>
        <Panel title="Notices due soon" actions={<Link to="/notices" search={{ view: "list" }} className="text-xs text-primary hover:underline">View all</Link>}>
          <ul className="space-y-3">
            {myNotices.filter((n) => !["Replied", "Closed"].includes(noticeStatus(n))).sort((a, b) => a.due.localeCompare(b.due)).slice(0, 8).map((n) => {
              const c = clients.find((x) => x.id === n.clientId);
              const d = daysBetween(new Date().toISOString(), n.due);
              return (
                <li key={n.id}>
                  <Link to="/notices" search={{ view: "list", open: n.id }} className="flex items-start justify-between gap-3 rounded-md p-1 hover:bg-accent/40">
                    <div>
                      <div className="text-sm font-medium"><Term k={n.form} /></div>
                      <div className="text-xs text-muted-foreground">{c?.name}</div>
                    </div>
                    <div className="text-right">
                      <StatusBadge status={noticeStatus(n, new Date(), soon)} label={d < 0 ? `${-d} days overdue` : d === 0 ? "Due today" : `Due in ${d} days`} />
                      <div className="mt-1 text-[11px] text-muted-foreground">{fmtDate(n.due)}</div>
                    </div>
                  </Link>
                </li>
              );
            })}
            {!myNotices.some((n) => !n.replied) && <li className="text-sm text-muted-foreground">No open notices.</li>}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
