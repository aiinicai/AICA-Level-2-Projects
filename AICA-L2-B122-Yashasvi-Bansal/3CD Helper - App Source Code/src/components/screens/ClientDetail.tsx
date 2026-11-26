import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { ArrowLeft, CalendarPlus, Pencil, Archive, ArchiveRestore, ChevronRight, Lock, Phone, Mail, MapPin, FileSpreadsheet, Trash2 } from "lucide-react";
import { DeleteClientDialog } from "@/components/DeleteClientDialog";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useTeam } from "@/hooks/useTeam";
import { useToast } from "@/components/Toast";
import { Alert, Badge, Button, Card, CardHeader, EmptyState, Field, Modal, PageHeader, PageLoader, Select } from "@/components/ui";
import { ClientForm, ClientRecord } from "@/components/ClientForm";
import { ENGAGEMENT_STATUS, canEdit, isAdmin, errMsg, logActivity } from "@/lib/db";
import { assessmentYearOptions, formatDate, formatDateTime, previousYearOf } from "@/lib/format";

export default function ClientDetail() {
  const { clientId } = useParams({ strict: false }) as { clientId?: string };
  const { firm, role } = useFirm();
  const { nameOf, members } = useTeam();
  const toast = useToast();
  const nav = useNavigate();
  const [client, setClient] = useState<ClientRecord | null>(null);
  const [engs, setEngs] = useState<any[]>([]);
  const [partyCount, setPartyCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [edit, setEdit] = useState(false);
  const [newAy, setNewAy] = useState(false);
  const [del, setDel] = useState(false);

  const load = async () => {
    const [c, e, p] = await Promise.all([
      supabase.from("clients").select("*").eq("id", clientId!).maybeSingle(),
      supabase.from("engagements").select("*").eq("client_id", clientId!).order("assessment_year", { ascending: false }),
      supabase.from("party_master").select("id", { count: "exact", head: true }).eq("client_id", clientId!),
    ]);
    setClient(c.data as ClientRecord);
    setEngs(e.data ?? []);
    setPartyCount(p.count ?? 0);
    setLoading(false);
  };
  useEffect(() => { load(); }, [clientId]);

  if (loading) return <PageLoader />;
  if (!client) return <EmptyState title="Client not found" action={<Link to="/app/clients"><Button>Back to clients</Button></Link>} />;

  const toggleArchive = async () => {
    const { error } = await supabase.from("clients").update({ archived: !client.archived }).eq("id", client.id!);
    if (error) return toast(errMsg(error), "error");
    await logActivity(firm!.id, "client.archived", "client", client.id, { name: client.name, archived: !client.archived });
    toast(client.archived ? "Client restored" : "Client archived");
    load();
  };

  return (
    <>
      <PageHeader
        back={<Link to="/app/clients" className="mb-2 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="h-4 w-4" />Clients</Link>}
        title={<span className="flex items-center gap-2">{client.name}{client.archived && <Badge className="bg-slate-200 text-slate-700">Archived</Badge>}</span>}
        subtitle={<span className="font-mono">{client.pan || "PAN not added"}</span>}
        actions={canEdit(role) && (
          <>
            <Button variant="outline" icon={<Pencil className="h-4 w-4" />} onClick={() => setEdit(true)}>Edit</Button>
            <Button variant="ghost" icon={client.archived ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />} onClick={toggleArchive}>{client.archived ? "Restore" : "Archive"}</Button>
            {isAdmin(role) && <Button variant="ghost" className="text-red-600" icon={<Trash2 className="h-4 w-4" />} onClick={() => setDel(true)}>Delete</Button>}
            <Button icon={<CalendarPlus className="h-4 w-4" />} onClick={() => setNewAy(true)}>New assessment year</Button>
          </>
        )}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Assessment years" subtitle="Each year has its own uploads, review and Clause 44 & 31 reports" />
          {engs.length === 0 ? (
            <EmptyState icon={<FileSpreadsheet className="h-7 w-7" />} title="No assessment year yet" text="Create an assessment year to upload the expense ledger."
              action={canEdit(role) && <Button icon={<CalendarPlus className="h-4 w-4" />} onClick={() => setNewAy(true)}>New assessment year</Button>} />
          ) : (
            <ul className="divide-y divide-slate-100">
              {engs.map((e) => (
                <li key={e.id}>
                  <Link to="/app/engagements/$engagementId" params={{ engagementId: e.id }} className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50">
                    <div className="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-xl bg-navy-950 text-white">
                      <span className="text-[9px] uppercase tracking-wider text-navy-300">AY</span>
                      <span className="text-xs font-bold">{e.assessment_year.slice(2)}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 font-medium">AY {e.assessment_year} {e.locked && <Lock className="h-3.5 w-3.5 text-emerald-700" />}</div>
                      <div className="text-xs text-slate-500">
                        Prepared by {nameOf(e.created_by)} · Assigned: {e.assigned_to ? nameOf(e.assigned_to) : "—"}
                        {e.reviewed_by && <> · Reviewed by {nameOf(e.reviewed_by)}</>}
                      </div>
                      <div className="text-xs text-slate-400">Last edited by {nameOf(e.updated_by)} · {formatDateTime(e.updated_at)}</div>
                    </div>
                    <Badge className={ENGAGEMENT_STATUS[e.status]?.cls}>{ENGAGEMENT_STATUS[e.status]?.label}</Badge>
                    <ChevronRight className="h-4 w-4 text-slate-400" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader title="Client details" />
          <dl className="space-y-3 px-5 py-4 text-sm">
            <div><dt className="text-xs text-slate-500">Status</dt><dd className="font-medium">{client.status}</dd></div>
            <div><dt className="text-xs text-slate-500">GSTIN(s)</dt><dd className="font-mono text-xs">{client.gstins?.length ? client.gstins.join(", ") : "—"}</dd></div>
            {client.contact_person && <div><dt className="text-xs text-slate-500">Contact</dt><dd>{client.contact_person}</dd></div>}
            {client.mobile && <div className="flex items-center gap-2"><Phone className="h-4 w-4 text-slate-400" />{client.mobile}</div>}
            {client.email && <div className="flex items-center gap-2"><Mail className="h-4 w-4 text-slate-400" />{client.email}</div>}
            {client.address && <div className="flex items-start gap-2"><MapPin className="mt-0.5 h-4 w-4 text-slate-400" />{client.address}</div>}
            <div><dt className="text-xs text-slate-500">Party master</dt><dd>{partyCount} parties (shared across all years)</dd></div>
            <div className="border-t border-slate-100 pt-3 text-xs text-slate-500">
              Added by {nameOf(client.created_by)} on {formatDate(client.created_at)}<br />
              Last edited by {nameOf(client.updated_by)} · {formatDateTime(client.updated_at)}
            </div>
            {client.notes && <div className="rounded-lg bg-slate-50 p-3 text-slate-700">{client.notes}</div>}
          </dl>
        </Card>
      </div>

      {edit && <ClientForm client={client} onClose={() => setEdit(false)} onSaved={() => { setEdit(false); load(); }} />}
      {newAy && (
        <NewEngagement clientId={client.id!} existing={engs.map((e) => e.assessment_year)} members={members}
          onClose={() => setNewAy(false)} onCreated={(id) => nav({ to: "/app/engagements/$engagementId", params: { engagementId: id } })} hasParties={partyCount > 0} />
      )}
      {del && <DeleteClientDialog client={{ id: client.id!, name: client.name, pan: client.pan }} engagements={engs} onClose={() => setDel(false)} onDeleted={() => nav({ to: "/app/clients" })} />}
    </>
  );
}

function NewEngagement({ clientId, existing, members, onClose, onCreated, hasParties }: {
  clientId: string; existing: string[]; members: { user_id: string; full_name: string | null; email: string | null; role: string }[];
  onClose: () => void; onCreated: (id: string) => void; hasParties: boolean;
}) {
  const { firm } = useFirm();
  const toast = useToast();
  const options = assessmentYearOptions().filter((a) => !existing.includes(a));
  const [ay, setAy] = useState(options[1] ?? options[0] ?? "");
  const [assignee, setAssignee] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true); setErr("");
    const { data, error } = await supabase.from("engagements").insert({
      client_id: clientId, firm_id: firm!.id, assessment_year: ay,
      assigned_to: assignee || null,
    }).select("id").single();
    setSaving(false);
    if (error) { setErr(/duplicate/i.test(error.message) ? "This assessment year already exists." : errMsg(error)); return; }
    await logActivity(firm!.id, "engagement.created", "engagement", data.id, { ay });
    toast(`AY ${ay} created`);
    onCreated(data.id);
  };

  return (
    <Modal open onClose={onClose} title="New assessment year"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button type="submit" form="ay-form" loading={saving} disabled={!ay}>Create</Button></>}>
      <form id="ay-form" onSubmit={submit} className="space-y-4">
        <Field label="Assessment year" hint={ay ? `Previous year (FY) ${previousYearOf(ay)}` : undefined}>
          <Select value={ay} onChange={(e) => setAy(e.target.value)}>{options.map((o) => <option key={o} value={o}>AY {o}</option>)}</Select>
        </Field>
        <Field label="Assign to">
          <Select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
            <option value="">Not assigned</option>
            {members.filter((m) => m.role !== "viewer").map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name || m.email}</option>)}
          </Select>
        </Field>
        {hasParties && <Alert tone="success">The client's party master (GSTINs, composition & exempt flags) and saved column mappings carry forward automatically to this year.</Alert>}
        {err && <Alert tone="error">{err}</Alert>}
      </form>
    </Modal>
  );
}
