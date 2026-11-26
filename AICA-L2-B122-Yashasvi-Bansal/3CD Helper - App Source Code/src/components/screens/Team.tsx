import { FormEvent, useEffect, useState } from "react";
import { UserPlus, Trash2, Mail, Copy } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useAuth } from "@/contexts/AuthContext";
import { useTeam } from "@/hooks/useTeam";
import { useToast } from "@/components/Toast";
import { Alert, Avatar, Badge, Button, Card, CardHeader, Field, Input, Modal, PageHeader, Select, Spinner } from "@/components/ui";
import { ROLE_LABEL, Role, errMsg, isAdmin, logActivity } from "@/lib/db";
import { formatDate } from "@/lib/format";

const ROLE_HELP: Record<Role, string> = {
  owner: "Everything, including firm settings and team",
  partner: "All client work, review, mark Final and unlock",
  staff: "Add clients, upload and review data",
  viewer: "Read-only access",
};

export default function Team() {
  const { firm, role } = useFirm();
  const { user } = useAuth();
  const { members, loading, reload } = useTeam();
  const toast = useToast();
  const [invites, setInvites] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [remove, setRemove] = useState<any>(null);
  const [workload, setWorkload] = useState<Record<string, { open: number; final: number; created: number }>>({});

  const loadInvites = () => {
    if (!firm || !isAdmin(role)) return;
    supabase.from("invitations").select("*").eq("firm_id", firm.id).eq("status", "pending").order("created_at", { ascending: false }).then(({ data }) => setInvites(data ?? []));
  };
  useEffect(() => {
    loadInvites();
    if (!firm) return;
    supabase.from("engagements").select("assigned_to, created_by, status").eq("firm_id", firm.id).then(({ data }) => {
      const w: Record<string, { open: number; final: number; created: number }> = {};
      const get = (id: string) => (w[id] ??= { open: 0, final: 0, created: 0 });
      (data ?? []).forEach((e: any) => {
        if (e.assigned_to) e.status === "final" ? get(e.assigned_to).final++ : get(e.assigned_to).open++;
        if (e.created_by) get(e.created_by).created++;
      });
      setWorkload(w);
    });
  }, [firm?.id, role]);

  const changeRole = async (userId: string, newRole: Role) => {
    const { error } = await supabase.from("firm_members").update({ role: newRole }).eq("firm_id", firm!.id).eq("user_id", userId);
    if (error) return toast(errMsg(error), "error");
    await logActivity(firm!.id, "member.role_changed", "member", userId, { role: newRole });
    toast("Role updated"); reload();
  };

  const appUrl = `${window.location.origin}/signup`;

  return (
    <>
      <PageHeader title="Team" subtitle="Who can access this firm's clients"
        actions={isAdmin(role) && <Button icon={<UserPlus className="h-4 w-4" />} onClick={() => setOpen(true)}>Invite member</Button>} />

      <Card>
        {loading ? <div className="flex justify-center py-10"><Spinner /></div> : (
          <ul className="divide-y divide-slate-100">
            {members.map((m) => {
              const w = workload[m.user_id];
              return (
                <li key={m.user_id} className="flex flex-wrap items-center gap-4 px-5 py-4">
                  <Avatar name={m.full_name || m.email} className="h-10 w-10" />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium">{m.full_name || m.email}{m.user_id === user?.id && <span className="ml-2 text-xs text-slate-500">(you)</span>}</div>
                    <div className="text-xs text-slate-500">{m.email} · joined {formatDate(m.joined_at)}</div>
                    {w && <div className="mt-1 text-xs text-slate-500">{w.created} years prepared · {w.open} open assigned · {w.final} finalised</div>}
                  </div>
                  {role === "owner" && m.role !== "owner" ? (
                    <Select value={m.role} onChange={(e) => changeRole(m.user_id, e.target.value as Role)} className="w-44">
                      {(["partner", "staff", "viewer"] as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                    </Select>
                  ) : <Badge className="bg-navy-50 text-navy-800">{ROLE_LABEL[m.role]}</Badge>}
                  {role === "owner" && m.role !== "owner" && <Button size="sm" variant="ghost" className="text-red-600" icon={<Trash2 className="h-4 w-4" />} onClick={() => setRemove(m)}>Remove</Button>}
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      {isAdmin(role) && invites.length > 0 && (
        <Card className="mt-6">
          <CardHeader title="Pending invitations" subtitle="They join automatically when they sign up or sign in with this email" />
          <ul className="divide-y divide-slate-100">
            {invites.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm">
                <Mail className="h-4 w-4 text-slate-400" /><span className="flex-1 font-medium">{i.email}</span>
                <Badge>{ROLE_LABEL[i.role as Role]}</Badge>
                <Button size="sm" variant="ghost" onClick={async () => { await supabase.from("invitations").update({ status: "revoked" }).eq("id", i.id); loadInvites(); }}>Revoke</Button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card className="mt-6 p-5">
        <h3 className="font-semibold">Roles</h3>
        <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
          {(Object.keys(ROLE_HELP) as Role[]).map((r) => <div key={r}><dt className="font-medium">{ROLE_LABEL[r]}</dt><dd className="text-slate-500">{ROLE_HELP[r]}</dd></div>)}
        </dl>
      </Card>

      {open && <InviteModal appUrl={appUrl} onClose={() => setOpen(false)} onDone={() => { setOpen(false); loadInvites(); }} />}
      {remove && (
        <Modal open onClose={() => setRemove(null)} title="Remove member?"
          footer={<><Button variant="ghost" onClick={() => setRemove(null)}>Cancel</Button><Button variant="danger" onClick={async () => {
            const { error } = await supabase.from("firm_members").delete().eq("firm_id", firm!.id).eq("user_id", remove.user_id);
            if (error) return toast(errMsg(error), "error");
            await logActivity(firm!.id, "member.removed", "member", remove.user_id, { name: remove.full_name || remove.email });
            toast("Member removed"); setRemove(null); reload();
          }}>Remove</Button></>}>
          <p className="text-sm"><b>{remove.full_name || remove.email}</b> will lose access to this firm. Their past work stays attributed to them.</p>
        </Modal>
      )}
    </>
  );
}

function InviteModal({ appUrl, onClose, onDone }: { appUrl: string; onClose: () => void; onDone: () => void }) {
  const { firm } = useFirm();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("staff");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    const { error } = await supabase.from("invitations").insert({ firm_id: firm!.id, email: email.trim().toLowerCase(), role });
    setBusy(false);
    if (error) return toast(/duplicate|unique/i.test(error.message) ? "An invitation is already pending for this email." : errMsg(error), "error");
    await logActivity(firm!.id, "member.invited", "invitation", undefined, { email, role });
    setSent(true);
  };
  const message = `You've been invited to join ${firm?.name} on 3CD Helper. Sign up (or sign in) with ${email} here: ${appUrl}`;
  return (
    <Modal open onClose={sent ? onDone : onClose} title="Invite a team member"
      footer={sent ? <Button onClick={onDone}>Done</Button> : <><Button variant="ghost" onClick={onClose}>Cancel</Button><Button type="submit" form="inv" loading={busy}>Create invitation</Button></>}>
      {sent ? (
        <div className="space-y-4">
          <Alert tone="success">Invitation created. <b>{email}</b> joins your firm automatically after signing up or signing in with this email.</Alert>
          <Field label="Share this message (WhatsApp / email)">
            <div className="flex gap-2"><Input readOnly value={message} /><Button variant="outline" icon={<Copy className="h-4 w-4" />} onClick={() => navigator.clipboard?.writeText(message).then(() => toast("Copied"))}>Copy</Button></div>
          </Field>
        </div>
      ) : (
        <form id="inv" onSubmit={submit} className="space-y-4">
          <Field label="Email" required><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></Field>
          <Field label="Role" hint={ROLE_HELP[role]}>
            <Select value={role} onChange={(e) => setRole(e.target.value as Role)}>{(["partner", "staff", "viewer"] as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</Select>
          </Field>
        </form>
      )}
    </Modal>
  );
}
