import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Paperclip, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { NOTICE_STATUSES, type Client, type Notice } from "@/lib/gst/demo";
import { daysBetween, isoDay } from "@/lib/gst/format";
import { NOTICE_LIBRARY, libraryFor, noticeFromLibrary, noticeKey } from "@/lib/gst/notices";
import { deleteNotice, getState, saveNotice, useApp, useClients } from "@/lib/store";
import { StatusBadge } from "./common";

export const blankNotice = (client?: Client): Notice =>
  noticeFromLibrary({ id: "n-" + Math.random().toString(36).slice(2, 10), clientId: client?.id ?? "", gstin: client?.gstin ?? "", form: "", issued: isoDay(new Date()), due: "", assignedTo: client?.staff ?? "", status: "Open" });

const MAX_ATTACHMENT = 1.5 * 1024 * 1024;

export function NoticeDialog({ value, onClose }: { value: Notice; onClose: () => void }) {
  const clients = useClients();
  const users = useApp((s) => s.users);
  const isNew = !getState().notices.some((n) => n.id === value.id);
  const [n, setN] = useState<Notice>(value);
  const [dueGiven, setDueGiven] = useState(!isNew || !!value.due);
  const [err, setErr] = useState("");
  const set = (p: Partial<Notice>) => setN({ ...n, ...p });
  const lib = libraryFor(n.form);
  const client = clients.find((c) => c.id === n.clientId);
  const left = n.due ? daysBetween(new Date().toISOString(), n.due) : null;

  const pickForm = (form: string) => {
    const l = libraryFor(form);
    set({ form, subject: l?.nature ?? n.subject, priority: l?.priority ?? n.priority, action: l?.action ?? n.action });
  };
  const attach = async (which: "attachment" | "reply", f: File | undefined) => {
    if (!f) return;
    if (f.size > MAX_ATTACHMENT) return void toast.error("Attachments up to 1.5 MB can be kept in this browser. Compress the PDF and try again.");
    const dataUrl = await new Promise<string>((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result)); r.onerror = rej; r.readAsDataURL(f); });
    set({ [which]: { name: f.name, dataUrl } } as Partial<Notice>);
  };
  const save = () => {
    if (!n.clientId) return setErr("Choose the client.");
    if (!n.form.trim() || !n.ref.trim()) return setErr("Form and reference number are required.");
    const c = clients.find((x) => x.id === n.clientId)!;
    const final = noticeFromLibrary({ ...n, gstin: c.gstin, due: dueGiven ? n.due : "", repliedOn: n.status === "Replied" ? n.repliedOn ?? isoDay(new Date()) : n.repliedOn });
    const dup = getState().notices.find((x) => x.id !== final.id && noticeKey(x) === noticeKey(final));
    if (dup) return setErr("This notice (same form + reference + GSTIN) already exists.");
    saveNotice(final);
    toast.success(isNew ? `Notice added${!dueGiven ? " — reply due 30 days from issue" : ""}` : "Notice updated");
    onClose();
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isNew ? "Add notice" : `${n.form} — ${client?.name ?? ""}`}</DialogTitle>
          <DialogDescription>Pick the form — nature, priority and action come from the form library. If no reply date is given, it defaults to 30 days from issue.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="n-client">Client *</Label>
            <select id="n-client" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={n.clientId} onChange={(e) => {
              const c = clients.find((x) => x.id === e.target.value);
              const prevStaff = clients.find((x) => x.id === n.clientId)?.staff ?? "";
              // follow the client's assigned staff unless the user picked someone else
              set({ clientId: e.target.value, gstin: c?.gstin ?? "", assignedTo: !n.assignedTo || n.assignedTo === prevStaff ? c?.staff ?? "" : n.assignedTo });
            }}>
              <option value="">Choose client…</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.gstin})</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="n-form">Form *</Label>
            <select id="n-form" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={NOTICE_LIBRARY.some((l) => l.form === n.form) ? n.form : n.form ? "__other" : ""} onChange={(e) => e.target.value !== "__other" && pickForm(e.target.value)}>
              <option value="">Choose form…</option>
              {NOTICE_LIBRARY.map((l) => <option key={l.form} value={l.form}>{l.form} — {l.nature}</option>)}
              {n.form && !lib && <option value="__other">{n.form} (not in library)</option>}
            </select>
          </div>
          {lib && (
            <div className="rounded-md bg-muted p-3 text-xs text-muted-foreground sm:col-span-2">
              <b className="text-foreground">{lib.form}:</b> {lib.nature} → {lib.action}
              {lib.link && n.clientId && <> · <Link to="/workspace/$clientId" params={{ clientId: n.clientId }} search={{ tab: lib.link.toLowerCase() }} className="text-primary underline" onClick={onClose}>Open {lib.link} reconciliation</Link></>}
            </div>
          )}
          <div className="space-y-1.5 sm:col-span-2"><Label htmlFor="n-nature">Nature</Label><Input id="n-nature" value={n.subject} onChange={(e) => set({ subject: e.target.value })} /></div>
          <div className="space-y-1.5"><Label htmlFor="n-ref">Reference no *</Label><Input id="n-ref" className="font-mono" value={n.ref} onChange={(e) => set({ ref: e.target.value })} /></div>
          <div className="space-y-1.5"><Label htmlFor="n-tp">Tax period</Label><Input id="n-tp" placeholder="e.g. Oct-25 or FY 2024-25" value={n.taxPeriod} onChange={(e) => set({ taxPeriod: e.target.value })} /></div>
          <div className="space-y-1.5"><Label htmlFor="n-iss">Issue date</Label><Input id="n-iss" type="date" value={n.issued} onChange={(e) => set({ issued: e.target.value })} /></div>
          <div className="space-y-1.5">
            <Label htmlFor="n-due" className="flex items-center justify-between">Reply due date
              <label className="flex items-center gap-1 text-xs font-normal text-muted-foreground"><input type="checkbox" checked={dueGiven} onChange={(e) => setDueGiven(e.target.checked)} /> given in notice</label>
            </Label>
            <Input id="n-due" type="date" disabled={!dueGiven} value={dueGiven ? n.due : ""} onChange={(e) => set({ due: e.target.value })} />
            <p className="text-xs text-muted-foreground">{!dueGiven ? "Default: 30 days from the issue date." : left === null ? "" : left < 0 ? <span className="text-destructive">{-left} days overdue</span> : `${left} days left`}</p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="n-pr">Priority</Label>
            <select id="n-pr" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={n.priority} onChange={(e) => set({ priority: e.target.value as Notice["priority"] })}>
              {["Critical", "High", "Medium", "Low"].map((p) => <option key={p}>{p}</option>)}
            </select>
          </div>
          <div className="space-y-1.5"><Label htmlFor="n-amt">Amount (₹)</Label><Input id="n-amt" type="number" value={n.amount} onChange={(e) => set({ amount: Number(e.target.value) || 0 })} /></div>
          <div className="space-y-1.5 sm:col-span-2"><Label htmlFor="n-act">Action required</Label><Input id="n-act" value={n.action} onChange={(e) => set({ action: e.target.value })} /></div>
          <div className="space-y-1.5"><Label htmlFor="n-ps">Portal status</Label><Input id="n-ps" value={n.portalStatus} onChange={(e) => set({ portalStatus: e.target.value })} /></div>
          <div className="space-y-1.5">
            <Label htmlFor="n-src">Source</Label>
            <select id="n-src" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={n.source} onChange={(e) => set({ source: e.target.value as Notice["source"] })}>
              {["Manual", "GSP notices API", "Template upload"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="n-as">Assigned to</Label>
            <select id="n-as" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={n.assignedTo} onChange={(e) => set({ assignedTo: e.target.value })}>
              <option value="">(unassigned)</option>
              {users.map((u) => <option key={u.id} value={u.name}>{u.name}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="n-st">Internal status</Label>
            <select id="n-st" className="h-9 w-full rounded-md border bg-background px-2 text-sm" value={n.status} onChange={(e) => set({ status: e.target.value as Notice["status"] })}>
              {NOTICE_STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="space-y-1.5 sm:col-span-2"><Label htmlFor="n-notes">Notes</Label><Textarea id="n-notes" rows={3} value={n.notes} onChange={(e) => set({ notes: e.target.value })} /></div>
          {(["attachment", "reply"] as const).map((w) => (
            <div key={w} className="space-y-1.5">
              <Label>{w === "attachment" ? "Notice PDF" : "Reply"}</Label>
              {n[w] ? (
                <div className="flex items-center gap-2 text-sm">
                  <a href={n[w]!.dataUrl} download={n[w]!.name} className="truncate text-primary underline">{n[w]!.name}</a>
                  <Button size="icon" variant="ghost" className="h-7 w-7" aria-label="Remove attachment" onClick={() => set({ [w]: undefined } as Partial<Notice>)}><Trash2 className="h-3.5 w-3.5" /></Button>
                </div>
              ) : (
                <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground hover:bg-accent/40">
                  <Paperclip className="h-4 w-4" /> Attach file
                  <input type="file" accept=".pdf,.jpg,.jpeg,.png,.docx" className="hidden" onChange={(e) => void attach(w, e.target.files?.[0])} />
                </label>
              )}
            </div>
          ))}
        </div>
        {err && <p className="text-sm text-destructive">{err}</p>}
        <DialogFooter className="flex-wrap gap-2 sm:justify-between">
          <div>{!isNew && <Button variant="ghost" className="text-destructive" onClick={() => { if (confirm("Delete this notice?")) { deleteNotice(n.id); onClose(); } }}>Delete</Button>}</div>
          <div className="flex gap-2">
            {!isNew && n.status !== "Replied" && <Button variant="outline" onClick={() => { saveNotice({ ...n, status: "Replied", replied: true, repliedOn: isoDay(new Date()) }); toast.success("Marked as replied"); onClose(); }}>Mark replied</Button>}
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button onClick={save}>Save notice</Button>
          </div>
        </DialogFooter>
        {!isNew && <div className="text-xs text-muted-foreground">Current status: <StatusBadge status={n.status} /></div>}
      </DialogContent>
    </Dialog>
  );
}
