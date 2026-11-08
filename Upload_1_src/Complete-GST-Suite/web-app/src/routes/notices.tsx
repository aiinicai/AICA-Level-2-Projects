import { useEffect, useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Bell, ChevronLeft, ChevronRight, Download, Mail, Plus, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Kpi, PageHeader, Panel, StatusBadge, Term, toneFor } from "@/components/gst/common";
import { DataTable } from "@/components/gst/DataTable";
import { NoticeDialog, blankNotice } from "@/components/gst/NoticeDialog";
import type { Notice } from "@/lib/gst/demo";
import { daysBetween, fmtDate, inr, isoDay } from "@/lib/gst/format";
import { daysLeft, noticeFromLibrary, noticeStatus } from "@/lib/gst/notices";
import { parseNoticeRows } from "@/lib/gst/parsers";
import { downloadTemplate } from "@/lib/exports";
import { addNotices, checkNotices, getState, log, useApp, useClients } from "@/lib/store";
import { cn } from "@/lib/utils";

type Search = { view: string; status?: string | undefined; open?: string | undefined };

export const Route = createFileRoute("/notices")({
  validateSearch: (s: Record<string, unknown>): Search => ({
    view: s["view"] === "calendar" ? "calendar" : "list",
    status: typeof s["status"] === "string" ? s["status"] : undefined,
    open: typeof s["open"] === "string" ? s["open"] : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Notices — Complete GST Suite" },
      { name: "description", content: "Track every GST notice — ADT-01, DRC-01B, DRC-01C, ASMT-10 and more — with due dates, priority and reply status." },
      { property: "og:title", content: "Notices — Complete GST Suite" },
      { property: "og:description", content: "Track every GST notice with due dates and reply status." },
    ],
  }),
  component: NoticesPage,
});

const DOT: Record<string, string> = {
  success: "bg-success/15 text-success border-success/30",
  warning: "bg-warning/20 text-warning-foreground border-warning/40",
  danger: "bg-destructive/12 text-destructive border-destructive/30",
  info: "bg-info/12 text-info border-info/30",
  neutral: "bg-muted text-muted-foreground",
};

function NoticesPage() {
  const { view, status, open } = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });
  const clients = useClients();
  const all = useApp((s) => s.notices);
  const soon = useApp((s) => s.prefs.reminderDays);
  const emailDays = useApp((s) => s.prefs.emailReminderDays);
  const users = useApp((s) => s.users);
  const progress = useApp((s) => s.progress);
  const [editing, setEditing] = useState<Notice | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const ids = new Set(clients.map((c) => c.id));
  const notices = all.filter((n) => ids.has(n.clientId));
  const nameOf = (id: string) => clients.find((c) => c.id === id)?.name ?? "";
  const chip = (n: Notice) => noticeStatus(n, new Date(), soon);
  const count = (st: string) => notices.filter((n) => chip(n) === st).length;
  const shown = status ? notices.filter((n) => (status === "Open" ? ["Open", "Due soon", "Overdue"].includes(chip(n)) : chip(n) === status)) : notices;
  const running = Object.values(progress).some((p) => p === "running" || p === "queued");

  useEffect(() => {
    if (open) {
      const n = all.find((x) => x.id === open);
      if (n) setEditing(n);
    }
  }, [open, all]);

  async function upload(f: File) {
    try {
      const { readSheetRows } = await import("@/lib/gst/excel");
      const parsed = parseNoticeRows(await readSheetRows(f));
      const unknown: string[] = [];
      const list = parsed.flatMap((p) => {
        const c = clients.find((x) => x.gstin === p.gstin);
        if (!c) { unknown.push(p.gstin || "(blank GSTIN)"); return []; }
        return [noticeFromLibrary({ ...p, clientId: c.id, gstin: c.gstin, assignedTo: p.assignedTo || c.staff })];
      });
      const added = addNotices(list);
      log(`Notices template uploaded: ${added} new, ${list.length - added} duplicate(s), ${unknown.length} unknown GSTIN(s)`);
      toast.success(`${added} new notice(s) added, ${list.length - added} duplicate(s) skipped`, { description: unknown.length ? `Skipped — GSTIN not among your clients: ${[...new Set(unknown)].join(", ")}` : undefined });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not read the template");
    }
  }

  function reminders() {
    const due = notices.filter((n) => !n.replied && n.assignedTo && daysLeft(n) <= emailDays);
    if (!due.length) return void toast.info(`No open notices due within ${emailDays} day(s).`);
    const by = new Map<string, Notice[]>();
    for (const n of due) by.set(n.assignedTo, [...(by.get(n.assignedTo) ?? []), n]);
    for (const [staff, list] of by) {
      const u = users.find((x) => x.name === staff);
      const body = list.map((n) => `- ${n.form} (${n.subject}) for ${nameOf(n.clientId)}, ref ${n.ref}: reply due ${fmtDate(n.due)} (${daysLeft(n) < 0 ? `${-daysLeft(n)} days overdue` : `${daysLeft(n)} days left`}). Action: ${n.action}`).join("\n");
      window.open(`mailto:${encodeURIComponent(u?.email ?? "")}?subject=${encodeURIComponent(`[GST] ${list.length} notice(s) due soon`)}&body=${encodeURIComponent(`Hi ${staff},\n\nThese GST notices need your reply:\n\n${body}\n\n— ${getState().firm?.name ?? "Complete GST Suite"}`)}`, "_blank");
    }
    log(`Reminder e-mails prepared for ${by.size} staff member(s) (${due.length} notices)`);
  }

  return (
    <div>
      <PageHeader
        title="Notices"
        subtitle="Every GST notice across your clients, nearest reply date first."
        actions={
          <>
            <Button variant="outline" onClick={() => void downloadTemplate("notices")}><Download className="mr-2 h-4 w-4" /> Template</Button>
            <Button variant="outline" onClick={() => file.current?.click()}><Upload className="mr-2 h-4 w-4" /> Upload template</Button>
            <input ref={file} type="file" accept=".xlsx,.xlsm,.csv" className="hidden" aria-label="Notices template" onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); e.target.value = ""; }} />
            <Button variant="outline" disabled={running} onClick={() => void checkNotices().then((r) => toast.success(`${r.added} new notice(s) from the GSP`, { description: r.skipped.length ? r.skipped.join("; ") : undefined }))}><Bell className="mr-2 h-4 w-4" /> Check GSP</Button>
            <Button variant="outline" onClick={reminders}><Mail className="mr-2 h-4 w-4" /> Remind staff</Button>
            <Button onClick={() => setEditing(blankNotice(clients[0]))} disabled={!clients.length}><Plus className="mr-2 h-4 w-4" /> Add notice</Button>
          </>
        }
      />
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {([["Overdue", "danger"], ["Due soon", "warning"], ["Open", undefined], ["Replied", "success"]] as const).map(([k, tone]) => (
          <Kpi key={k} label={k === "Due soon" ? `Due soon (${soon} days)` : k === "Open" ? "Open (incl. due soon / overdue)" : k} value={k === "Open" ? count("Open") + count("Due soon") + count("Overdue") : count(k)} tone={(k === "Replied" ? "success" : count(k) ? tone : undefined) as "danger" | "warning" | "success" | undefined} onClick={() => navigate({ search: { view: "list", status: status === k ? undefined : k } })} />
        ))}
      </div>
      <div className="mb-4 flex items-center gap-2">
        <div className="inline-flex rounded-md border p-0.5" role="tablist">
          {(["list", "calendar"] as const).map((v) => (
            <button key={v} role="tab" aria-selected={view === v} onClick={() => navigate({ search: { view: v, status } })} className={cn("rounded px-4 py-1.5 text-sm capitalize", view === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>{v}</button>
          ))}
        </div>
        {status && <Button size="sm" variant="ghost" onClick={() => navigate({ search: { view } })}>Showing “{status}” · clear</Button>}
      </div>
      {view === "calendar" ? (
        <CalendarView notices={shown} chip={chip} nameOf={nameOf} onSelect={setEditing} />
      ) : (
        <Panel>
          <DataTable
            rows={[...shown].sort((a, b) => Number(a.replied) - Number(b.replied) || a.due.localeCompare(b.due))}
            rowKey={(n) => n.id}
            exportName="notices"
            onRowClick={setEditing}
            empty={{ message: "No notices yet. Add one, upload the notices template, or check the GSP.", action: <Button size="sm" onClick={() => setEditing(blankNotice(clients[0]))} disabled={!clients.length}>Add notice</Button> }}
            columns={[
              { key: "chip", title: "Status", header: "Status", value: (n) => chip(n), filter: true, cell: (n) => <StatusBadge status={chip(n)} /> },
              { key: "client", title: "Client", header: "Client", value: (n) => nameOf(n.clientId), filter: true, cell: (n) => <span>{nameOf(n.clientId)}<div className="font-mono text-[11px] text-muted-foreground">{n.gstin}</div></span> },
              { key: "form", title: "Form", header: "Form", value: (n) => n.form, filter: true, cell: (n) => <Term k={n.form} /> },
              { key: "nature", title: "Nature", header: "Nature", value: (n) => n.subject, cell: (n) => <span>{n.subject}<div className="font-mono text-[11px] text-muted-foreground">{n.ref}</div></span> },
              { key: "period", title: "Tax period", header: "Tax period", value: (n) => n.taxPeriod },
              { key: "issued", title: "Issue date", header: "Issued", value: (n) => n.issued, cell: (n) => <span className="whitespace-nowrap">{fmtDate(n.issued)}</span> },
              { key: "due", title: "Reply due date", header: "Reply due", value: (n) => n.due, cell: (n) => <span className="whitespace-nowrap">{fmtDate(n.due)}</span> },
              { key: "left", title: "Days left", header: "Days left", value: (n) => daysLeft(n), align: "right", cell: (n) => (n.replied ? "—" : <span className={daysLeft(n) < 0 ? "text-destructive" : daysLeft(n) <= soon ? "text-warning-foreground" : ""}>{daysLeft(n)}</span>) },
              { key: "priority", title: "Priority", header: "Priority", value: (n) => n.priority, filter: true },
              { key: "action", title: "Action required", header: "Action required", value: (n) => n.action, cell: (n) => <span className="text-xs">{n.action}</span> },
              { key: "portal", title: "Portal status", header: "Portal status", value: (n) => n.portalStatus },
              { key: "source", title: "Source", header: "Source", value: (n) => n.source, filter: true },
              { key: "assigned", title: "Assigned to", header: "Assigned to", value: (n) => n.assignedTo, filter: true },
              { key: "status", title: "Internal status", header: "Internal status", value: (n) => n.status, filter: true },
              { key: "amount", title: "Amount", header: "Amount", value: (n) => n.amount, money: true, align: "right", cell: (n) => (n.amount ? inr(n.amount) : "—") },
              { key: "notes", title: "Notes", header: "Notes", value: (n) => n.notes, cell: (n) => <span className="line-clamp-2 max-w-56 text-xs text-muted-foreground">{n.notes}</span> },
            ]}
          />
        </Panel>
      )}
      {editing && <NoticeDialog value={editing} onClose={() => { setEditing(null); if (open) navigate({ search: { view, status } }); }} />}
    </div>
  );
}

function CalendarView({ notices, chip, nameOf, onSelect }: { notices: Notice[]; chip: (n: Notice) => string; nameOf: (id: string) => string; onSelect: (n: Notice) => void }) {
  const now = new Date();
  const [cursor, setCursor] = useState(new Date(now.getFullYear(), now.getMonth(), 1));
  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const startPad = (new Date(year, month, 1).getDay() + 6) % 7;
  const days = new Date(year, month + 1, 0).getDate();
  const cells: (Date | null)[] = [...Array(startPad).fill(null), ...Array.from({ length: days }, (_, i) => new Date(year, month, i + 1))];
  while (cells.length % 7) cells.push(null);
  const todayIso = isoDay(now);
  return (
    <Panel
      title={cursor.toLocaleDateString("en-IN", { month: "long", year: "numeric" })}
      actions={
        <div className="flex items-center gap-1">
          <Button size="icon" variant="ghost" aria-label="Previous month" onClick={() => setCursor(new Date(year, month - 1, 1))}><ChevronLeft className="h-4 w-4" /></Button>
          <Button size="sm" variant="ghost" onClick={() => setCursor(new Date(now.getFullYear(), now.getMonth(), 1))}>Today</Button>
          <Button size="icon" variant="ghost" aria-label="Next month" onClick={() => setCursor(new Date(year, month + 1, 1))}><ChevronRight className="h-4 w-4" /></Button>
        </div>
      }
    >
      <div className="grid grid-cols-7 gap-px overflow-hidden rounded-md border bg-border text-sm">
        {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => <div key={d} className="bg-muted px-2 py-1.5 text-xs font-medium text-muted-foreground">{d}</div>)}
        {cells.map((d, i) => {
          const iso = d ? isoDay(d) : "";
          const due = d ? notices.filter((n) => n.due === iso) : [];
          return (
            <div key={i} className={cn("min-h-24 bg-card p-1.5", !d && "bg-muted/40")}>
              {d && (
                <>
                  <div className={cn("mb-1 flex h-6 w-6 items-center justify-center rounded-full text-xs", iso === todayIso ? "bg-primary font-semibold text-primary-foreground" : "text-muted-foreground")}>{d.getDate()}</div>
                  <div className="space-y-1">
                    {due.map((n) => (
                      <button key={n.id} onClick={() => onSelect(n)} title={`${n.form} — ${nameOf(n.clientId)} — ${n.subject}`} className={cn("block w-full truncate rounded border px-1.5 py-0.5 text-left text-[11px] font-medium", DOT[toneFor(chip(n))])}>
                        {n.form} · {nameOf(n.clientId).split(" ")[0]}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-3 text-xs">{["Overdue", "Due soon", "Open", "Replied"].map((s) => <StatusBadge key={s} status={s} />)}</div>
      <p className="mt-2 text-xs text-muted-foreground">{notices.filter((n) => daysBetween(isoDay(cursor), n.due) >= 0 && n.due.slice(0, 7) === isoDay(cursor).slice(0, 7)).length} reply date(s) this month.</p>
    </Panel>
  );
}
