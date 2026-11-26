import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearch } from "@tanstack/react-router";
import { ArrowLeft, Database, Upload, ListChecks, Users2, FileBarChart, MessageSquare, Lock, Unlock, Send, ShieldCheck, Settings2, Trash2, Download, FileSpreadsheet } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useAuth } from "@/contexts/AuthContext";
import { useTeam } from "@/hooks/useTeam";
import { useToast } from "@/components/Toast";
import { useClause44Summary } from "@/hooks/useClause44";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, Field, Input, Modal, PageHeader, PageLoader, Select, Tabs, Textarea } from "@/components/ui";
import { UploadWizard } from "@/components/c44/UploadWizard";
import { ClientLinkPanel } from "@/components/ClientLinkPanel";
import { ReviewTab } from "@/components/c44/ReviewTab";
import { PartiesTab } from "@/components/c44/PartiesTab";
import { ReportTab } from "@/components/c44/ReportTab";
import { C31Module } from "@/components/c31/C31Module";
import { YearImport } from "@/components/YearImport";
import { DriveInbox } from "@/components/DriveInbox";
import { syncLedgerYear } from "@/lib/c44/ledgerStore";
import { ACTION_LABEL, ENGAGEMENT_STATUS, canEdit, errMsg, isAdmin, logActivity } from "@/lib/db";
import { formatDateTime, formatINR, previousYearOf } from "@/lib/format";

type Tab = "upload" | "review" | "parties" | "report" | "notes";

export default function Engagement() {
  const { engagementId } = useParams({ strict: false }) as { engagementId?: string };
  const search = useSearch({ strict: false }) as { tab?: string; m?: string };
  const navigate = useNavigate();
  const { firm, role } = useFirm();
  const { nameOf } = useTeam();
  const toast = useToast();
  const [eng, setEng] = useState<any>(null);
  const [client, setClient] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState<null | "final" | "unlock" | "details">(null);
  const [clientFile, setClientFile] = useState<File | null>(null);
  const [bulk, setBulk] = useState(false);
  const [driveFile, setDriveFile] = useState<File | null>(null);
  const { summary, reload: reloadSummary } = useClause44Summary(engagementId);

  const tab = (search.tab as Tab) || (summary.row_count ? "review" : "upload");
  const setTab = (t: Tab) => { navigate({ to: ".", search: (prev: Record<string, unknown>) => ({ ...prev, tab: t }), replace: true }); };
  const mod: "c44" | "c31" = search.m === "c31" ? "c31" : "c44";
  const setMod = (m: "c44" | "c31") => { navigate({ to: ".", search: (prev: Record<string, unknown>) => ({ ...prev, m, tab: undefined }), replace: true }); };

  const load = async () => {
    const { data } = await supabase.from("engagements").select("*, clients(*)").eq("id", engagementId!).maybeSingle();
    setEng(data);
    setClient(data?.clients ?? null);
    setLoading(false);
  };
  useEffect(() => { load(); }, [engagementId]);
  // Re-classify on open so party-master changes made from another year are reflected.
  useEffect(() => { if (eng && !eng.locked && canEdit(role)) supabase.rpc("reclassify_engagement", { p_eng: eng.id }).then(() => syncAndReload()); }, [eng?.id]);

  if (loading) return <PageLoader />;
  if (!eng) return <EmptyState title="Assessment year not found" action={<Link to="/app/clients"><Button>Back to clients</Button></Link>} />;

  const editable = !eng.locked && canEdit(role);
  const refreshAll = () => { load(); reloadSummary(); };
  /** After party master changes: bring this year's Tally ledger rows in step, then refresh the totals. */
  const syncAndReload = async () => {
    if (eng && !eng.locked && canEdit(role)) { try { await syncLedgerYear(eng); } catch { /* the Report tab shows any problem */ } }
    reloadSummary();
  };

  const setStatus = async (status: string) => {
    const { error } = await supabase.from("engagements").update({ status }).eq("id", eng.id);
    if (error) return toast(errMsg(error), "error");
    await logActivity(firm!.id, "engagement.status", "engagement", eng.id, { status, name: `${client?.name} ${eng.assessment_year}` });
    toast(status === "in_review" ? "Sent for review" : "Status updated");
    load();
  };

  return (
    <>
      <PageHeader
        back={<Link to="/app/clients/$clientId" params={{ clientId: eng.client_id }} className="mb-2 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" />{client?.name}</Link>}
        title={<span className="flex flex-wrap items-center gap-2">AY {eng.assessment_year}<Badge className={ENGAGEMENT_STATUS[eng.status]?.cls}>{eng.locked && <Lock className="h-3 w-3" />}{ENGAGEMENT_STATUS[eng.status]?.label}</Badge></span>}
        subtitle={<>FY {previousYearOf(eng.assessment_year)} · Prepared by {nameOf(eng.created_by)}{eng.assigned_to && <> · Assigned to {nameOf(eng.assigned_to)}</>}{eng.reviewed_by && <> · Reviewed by {nameOf(eng.reviewed_by)}</>}</>}
        actions={
          <>
            {canEdit(role) && <Button variant="outline" icon={<Settings2 className="h-4 w-4" />} onClick={() => setDialog("details")}>Details</Button>}
            {editable && eng.status === "draft" && <Button variant="secondary" icon={<Send className="h-4 w-4" />} onClick={() => setStatus("in_review")}>Send for review</Button>}
            {!eng.locked && isAdmin(role) && <Button icon={<ShieldCheck className="h-4 w-4" />} onClick={() => setDialog("final")}>Mark Final</Button>}
            {eng.locked && isAdmin(role) && <Button variant="outline" icon={<Unlock className="h-4 w-4" />} onClick={() => setDialog("unlock")}>Unlock</Button>}
          </>
        }
      />
      {eng.locked && <Alert tone="success" className="mb-4 flex items-center gap-2"><Lock className="h-4 w-4" />This year is Final and locked{eng.reviewed_by && <> – reviewed by <b>{nameOf(eng.reviewed_by)}</b> on {formatDateTime(eng.reviewed_at)}</>}. Unlock to make changes.</Alert>}
      {!eng.locked && eng.unlock_reason && <Alert tone="warn" className="mb-4">Reopened: {eng.unlock_reason}</Alert>}

      <div className="mb-5 flex flex-wrap items-center gap-2">
        {([["c44", "44", "GST break-up of expenditure"], ["c31", "31", "Loans · 269SS / 269T"]] as const).map(([k, no, t]) => (
          <button key={k} onClick={() => setMod(k)}
            className={`rounded-xl border px-4 py-2 text-left transition ${mod === k ? "border-navy-900 bg-navy-950 text-white shadow" : "border-slate-200 bg-white text-slate-700 hover:border-navy-300"}`}>
            <div className={`text-[10px] font-semibold uppercase tracking-wider ${mod === k ? "text-gold-400" : "text-slate-400"}`}>Clause {no}</div>
            <div className="text-sm font-semibold">{t}</div>
          </button>
        ))}
        {editable && !bulk && <Button className="ml-auto" variant="gold" icon={<Database className="h-4 w-4" />} onClick={() => { setDriveFile(null); setBulk(true); }}>Bring data (all clauses)</Button>}
      </div>
      {editable && !bulk && <DriveInbox eng={eng} client={client} onFile={(f) => { setDriveFile(f); setBulk(true); }} />}
      {bulk && <YearImport eng={eng} client={client} initialFile={driveFile} onClose={() => { setBulk(false); setDriveFile(null); refreshAll(); }}
        onDone={(last) => { setBulk(false); setDriveFile(null); refreshAll(); navigate({ to: ".", search: (prev: Record<string, unknown>) => ({ ...prev, m: last, tab: last === "c44" ? "report" : undefined }), replace: true }); toast("Data brought in"); }} />}
      {!bulk && mod === "c31" && <C31Module eng={eng} client={client} editable={editable} onEngChanged={load} />}
      {!bulk && mod === "c44" && (<>
      <Tabs<Tab>
        value={tab}
        onChange={setTab}
        tabs={[
          { key: "upload", label: "Upload", icon: <Upload className="h-4 w-4" /> },
          { key: "review", label: "Review", icon: <ListChecks className="h-4 w-4" />, badge: summary.row_count ? <Badge className="bg-navy-50 text-navy-800">{summary.row_count.toLocaleString("en-IN")}</Badge> : undefined },
          { key: "parties", label: "Party master", icon: <Users2 className="h-4 w-4" /> },
          { key: "report", label: "Clause 44 report", icon: <FileBarChart className="h-4 w-4" /> },
          { key: "notes", label: "Notes & activity", icon: <MessageSquare className="h-4 w-4" /> },
        ]}
      />
      <div className="mt-5">
        {tab === "upload" && (
          <div className="space-y-4">
            {editable ? <UploadWizard engagement={eng} clientId={eng.client_id} clientName={client?.name ?? ""} incoming={clientFile} onDone={() => { setClientFile(null); refreshAll(); setTab("review"); }} /> : <Alert tone="info">{eng.locked ? "Unlock this year to upload more data." : "You have read-only access."}</Alert>}
            {client && <ClientLinkPanel engagement={eng} client={client} module="clause44" editable={editable} onUse={(f) => { setClientFile(f); window.scrollTo({ top: 0, behavior: "smooth" }); }} />}
            <UploadsList engagementId={eng.id} editable={editable} onChanged={refreshAll} />
          </div>
        )}
        {tab === "review" && (summary.row_count === 0 ? <Card><EmptyState icon={<FileSpreadsheet className="h-7 w-7" />} title="No data yet" text="Upload the expense ledger to start." action={editable && <Button onClick={() => setTab("upload")}>Upload data</Button>} /></Card> :
          <ReviewTab engagementId={eng.id} editable={editable} summary={summary} onChanged={reloadSummary} />)}
        {tab === "parties" && <PartiesTab clientId={eng.client_id} engagementId={eng.id} editable={editable} onChanged={syncAndReload} />}
        {tab === "report" && <ReportTab engagement={eng} client={client} summary={summary} editable={canEdit(role)} onChanged={refreshAll} />}
        {tab === "notes" && <NotesTab engagementId={eng.id} />}
      </div>
      </>)}

      {dialog === "final" && <FinalDialog eng={eng} summary={summary} onClose={() => setDialog(null)} onDone={() => { setDialog(null); load(); }} />}
      {dialog === "unlock" && <UnlockDialog eng={eng} onClose={() => setDialog(null)} onDone={() => { setDialog(null); load(); }} />}
      {dialog === "details" && <DetailsDialog eng={eng} onClose={() => setDialog(null)} onDone={() => { setDialog(null); refreshAll(); }} />}
    </>
  );
}

function UploadsList({ engagementId, editable, onChanged }: { engagementId: string; editable: boolean; onChanged: () => void }) {
  const { firm } = useFirm();
  const { nameOf } = useTeam();
  const toast = useToast();
  const [list, setList] = useState<any[]>([]);
  const [del, setDel] = useState<any>(null);
  const load = () => supabase.from("uploads").select("*").eq("engagement_id", engagementId).eq("module", "clause44").order("created_at", { ascending: false }).then(({ data }) => setList(data ?? []));
  useEffect(() => { load(); }, [engagementId]);
  if (!list.length) return null;
  return (
    <Card>
      <CardHeader title="Uploaded files" subtitle="Deleting a file removes its entries from this year" />
      <ul className="divide-y divide-slate-100">
        {list.map((u) => (
          <li key={u.id} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm">
            <FileSpreadsheet className="h-5 w-5 text-navy-700" />
            <div className="min-w-0 flex-1">
              <div className="truncate font-medium">{u.file_name}</div>
              <div className="text-xs text-slate-500">{u.row_count.toLocaleString("en-IN")} entries · {u.software_detected} · by {nameOf(u.created_by)} · {formatDateTime(u.created_at)}</div>
            </div>
            {u.storage_path && (
              <Button size="sm" variant="ghost" icon={<Download className="h-4 w-4" />} onClick={async () => {
                const { data, error } = await supabase.storage.from("uploads").createSignedUrl(u.storage_path, 120);
                if (error || !data) return toast("Original file not available", "error");
                window.open(data.signedUrl, "_blank");
              }}>Original</Button>
            )}
            {editable && <Button size="sm" variant="ghost" className="text-red-600" icon={<Trash2 className="h-4 w-4" />} onClick={() => setDel(u)}>Delete</Button>}
          </li>
        ))}
      </ul>
      {del && (
        <Modal open onClose={() => setDel(null)} title="Delete upload?"
          footer={<><Button variant="ghost" onClick={() => setDel(null)}>Cancel</Button><Button variant="danger" onClick={async () => {
            const { error } = await supabase.from("uploads").delete().eq("id", del.id);
            if (error) return toast(errMsg(error), "error");
            if (del.storage_path) await supabase.storage.from("uploads").remove([del.storage_path]);
            await logActivity(firm!.id, "upload.deleted", "engagement", engagementId, { file: del.file_name });
            toast("Upload deleted"); setDel(null); load(); onChanged();
          }}>Delete</Button></>}>
          <p className="text-sm">This removes <b>{del.row_count}</b> entries imported from <b>{del.file_name}</b>, including any edits made to them. The party master is kept.</p>
        </Modal>
      )}
    </Card>
  );
}

function FinalDialog({ eng, summary, onClose, onDone }: { eng: any; summary: any; onClose: () => void; onDone: () => void }) {
  const { firm } = useFirm();
  const { user } = useAuth();
  const toast = useToast();
  const [udin, setUdin] = useState(eng.udin ?? "");
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const pl = eng.pl_total_expenditure === null ? null : Number(eng.pl_total_expenditure);
  const issues: string[] = [];
  if (summary.row_count === 0) issues.push("No data has been uploaded.");
  if (summary.invalid_gstin_count) issues.push(`${summary.invalid_gstin_count} entries have invalid GSTINs.`);
  if (pl === null) issues.push("P&L total expenditure is not entered (reconciliation pending).");
  else if (Math.abs(pl - summary.reported_total) >= 1) issues.push(`Difference with P&L: ${formatINR(pl - summary.reported_total)}.`);
  return (
    <Modal open onClose={onClose} title="Mark as Final"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} disabled={(issues.length > 0 && !ack) || summary.row_count === 0} icon={<Lock className="h-4 w-4" />} onClick={async () => {
        setBusy(true);
        const { error } = await supabase.from("engagements").update({ status: "final", locked: true, reviewed_by: user!.id, reviewed_at: new Date().toISOString(), udin: udin.trim() || null, unlock_reason: null }).eq("id", eng.id);
        setBusy(false);
        if (error) return toast(errMsg(error), "error");
        await logActivity(firm!.id, "engagement.locked", "engagement", eng.id, { ay: eng.assessment_year });
        toast("Marked Final and locked"); onDone();
      }}>Mark Final & lock</Button></>}>
      <div className="space-y-4">
        <p className="text-sm text-slate-600">You will be recorded as the reviewer. Entries, uploads and party flags for this year are locked against changes.</p>
        {issues.length > 0 && (
          <Alert tone="warn">
            <ul className="list-disc space-y-1 pl-4">{issues.map((i) => <li key={i}>{i}</li>)}</ul>
            {summary.row_count > 0 && <label className="mt-3 flex items-center gap-2 font-medium"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} />I have reviewed these points</label>}
          </Alert>
        )}
        <Field label="UDIN (optional)" hint="Can also be added after locking"><Input value={udin} onChange={(e) => setUdin(e.target.value.toUpperCase())} maxLength={18} className="font-mono" /></Field>
      </div>
    </Modal>
  );
}

function UnlockDialog({ eng, onClose, onDone }: { eng: any; onClose: () => void; onDone: () => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Modal open onClose={onClose} title="Unlock assessment year"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button disabled={reason.trim().length < 5} loading={busy} onClick={async () => {
        setBusy(true);
        const { error } = await supabase.from("engagements").update({ locked: false, status: "in_review", unlock_reason: reason.trim() }).eq("id", eng.id);
        setBusy(false);
        if (error) return toast(errMsg(error), "error");
        await logActivity(firm!.id, "engagement.unlocked", "engagement", eng.id, { reason: reason.trim() });
        toast("Unlocked"); onDone();
      }}>Unlock</Button></>}>
      <Field label="Reason for unlocking" required hint="Recorded in the activity log"><Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} /></Field>
    </Modal>
  );
}

function DetailsDialog({ eng, onClose, onDone }: { eng: any; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const { members } = useTeam();
  const [pl, setPl] = useState(eng.pl_total_expenditure ?? "");
  const [assigned, setAssigned] = useState(eng.assigned_to ?? "");
  const [udin, setUdin] = useState(eng.udin ?? "");
  const [busy, setBusy] = useState(false);
  return (
    <Modal open onClose={onClose} title="Assessment year details"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => {
        setBusy(true);
        const n = String(pl).trim() === "" ? null : Number(String(pl).replace(/,/g, ""));
        const payload = eng.locked ? { udin: udin.trim() || null } : { pl_total_expenditure: n, assigned_to: assigned || null, udin: udin.trim() || null };
        const { error } = await supabase.from("engagements").update(payload).eq("id", eng.id);
        setBusy(false);
        if (error) return toast(errMsg(error), "error");
        toast("Saved"); onDone();
      }}>Save</Button></>}>
      <div className="space-y-4">
        {eng.locked && <Alert tone="info">This year is locked – only UDIN can be changed.</Alert>}
        <Field label="Total expenditure as per P&L (₹)"><Input value={pl} disabled={eng.locked} onChange={(e) => setPl(e.target.value)} inputMode="decimal" /></Field>
        <Field label="Assigned to">
          <Select value={assigned} disabled={eng.locked} onChange={(e) => setAssigned(e.target.value)}>
            <option value="">Not assigned</option>
            {members.filter((m) => m.role !== "viewer").map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name || m.email}</option>)}
          </Select>
        </Field>
        <Field label="UDIN"><Input value={udin} onChange={(e) => setUdin(e.target.value.toUpperCase())} maxLength={18} className="font-mono" /></Field>
      </div>
    </Modal>
  );
}

function NotesTab({ engagementId }: { engagementId: string }) {
  const { firm, role } = useFirm();
  const { nameOf } = useTeam();
  const toast = useToast();
  const [notes, setNotes] = useState<any[]>([]);
  const [acts, setActs] = useState<any[]>([]);
  const [text, setText] = useState("");
  const load = () => {
    supabase.from("comments").select("*").eq("engagement_id", engagementId).is("row_id", null).order("created_at", { ascending: false }).then(({ data }) => setNotes(data ?? []));
    supabase.from("activity_log").select("*").eq("entity_id", engagementId).order("created_at", { ascending: false }).limit(100).then(({ data }) => setActs(data ?? []));
  };
  useEffect(() => { load(); }, [engagementId]);
  const add = async () => {
    const { error } = await supabase.from("comments").insert({ engagement_id: engagementId, firm_id: firm!.id, body: text.trim() });
    if (error) return toast(errMsg(error), "error");
    setText(""); load();
  };
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader title="Working-paper notes" subtitle="Visible to everyone in your firm" />
        <div className="p-5">
          {canEdit(role) && (<><Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. Composition status of XYZ confirmed from GST portal on 12-09-2025" rows={3} />
            <Button className="mt-2" size="sm" disabled={!text.trim()} onClick={add}>Add note</Button></>)}
          <ul className="mt-4 space-y-3">
            {notes.map((n) => <li key={n.id} className="rounded-xl bg-slate-50 p-3 text-sm"><div className="whitespace-pre-wrap">{n.body}</div><div className="mt-1 text-xs text-slate-500">{nameOf(n.created_by)} · {formatDateTime(n.created_at)}</div></li>)}
            {!notes.length && <li className="text-sm text-slate-500">No notes yet.</li>}
          </ul>
        </div>
      </Card>
      <Card>
        <CardHeader title="Activity on this year" />
        <ul className="space-y-3 p-5 text-sm">
          {acts.map((a) => (
            <li key={a.id}>
              <b>{nameOf(a.user_id)}</b> {ACTION_LABEL[a.action] ?? a.action}
              {a.details?.file && <> · {a.details.file}</>}{a.details?.rows && <> ({a.details.rows} rows)</>}{a.details?.reason && <> · “{a.details.reason}”</>}{a.details?.format && <> · {String(a.details.format).toUpperCase()}</>}
              <div className="text-xs text-slate-500">{formatDateTime(a.created_at)}</div>
            </li>
          ))}
          {!acts.length && <li className="text-slate-500">No activity yet.</li>}
        </ul>
      </Card>
    </div>
  );
}
